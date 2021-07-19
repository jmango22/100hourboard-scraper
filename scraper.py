from bs4 import BeautifulSoup
import requests
import json
import numpy as np
import io
from PIL import Image
import os

BASE_URL = 'http://100hourboard.org'
response = requests.get(BASE_URL + '/questions/archives/', timeout=5)
content = BeautifulSoup(response.content, "html.parser")

#print(content.prettify())

year_urls = []

for link in content.body.find('div', class_="flat_content").find_all('a'):
    year_url = BASE_URL + link.get('href')
    year_urls.append(year_url)

#print(*year_urls, sep='\n')

month_urls = []

for year_url in year_urls:
    year_response = requests.get(year_url, timeout=5)
    year_content = BeautifulSoup(year_response.content, "html.parser")
    for link in year_content.body.find('div', class_="flat_content").find_all('a'):
        month_url = BASE_URL + link.get('href')
        month_urls.append(month_url)

#print(*month_urls, sep='\n')

day_urls = []

for month_url in month_urls:
    month_response = requests.get(month_url, timeout=5)
    month_content = BeautifulSoup(month_response.content, "html.parser")
    for link in month_content.body.find('div', class_="flat_content").find_all('a'):
        day_url = BASE_URL + link.get('href')
        day_urls.append(day_url)

#print(*day_urls, sep='\n')

# now that we have a list of all the urls we will hit, it's time to parse out the posts

posts = []
for index, day_url in enumerate(day_urls):
    print("{:.2f}%".format((index/len(day_urls))*100))
    try:
        day_response = requests.get(day_url, timeout=5)
        day_content = BeautifulSoup(day_response.content, "html.parser")
        for post_raw in day_content.body.find_all('div', class_="post"):
            post = {}
            submission_info = post_raw.find('span', class_="submission_info")
            post['number'] = submission_info.find('a').text.replace('#', "")
            post['time'] = submission_info.text.split("posted on", 1)[1].replace('\n', "").strip()
            post['categories'] = []
            for category in post_raw.find_all('div', class_="category_tag"):
                post['categories'].append(category.text.replace('\n', ""))
            post['question'] = str(post_raw.find('div', class_="submission_text").find('p'))
            post['responses'] = []
            for response_raw in post_raw.find_all('div', class_="response"):
                response = {}
                writer = response_raw.find('div', class_="response_byline")
                if writer != None and writer.find('a') != None:
                    response['writer'] = {
                        "name": writer.find('a').text,
                        "number": writer.find('a').get('href')
                    }
                response_text = response_raw.find('div', class_="response_text")
                a_text = response_text.find('span', class_="leadin")
                if a_text != None:
                    a_text.decompose()
                response['response'] = ''
                for child in response_text.children:
                    response['response'] += str(child)
                # Scrap all the images in the response
                for image in response_text.find_all('img'):
                    image_url = image.get('src')
                    if image_url != None:
                        image_src = BASE_URL + image_url
                        file_path = '.'+image_url
                        if not os.path.isfile(file_path):
                            try:
                                image_content = requests.get(image_src).content
                            except Exception as e:
                                print(f"ERROR - Could not download {image_src} - {e}")
                            
                            try:
                                image_file = io.BytesIO(image_content)
                                image = Image.open(image_file).convert('RGB')
                                if not os.path.exists(os.path.dirname(file_path)):
                                    os.makedirs(os.path.dirname(file_path))
                                with open(file_path, 'wb') as f:
                                    image.save(f, "JPEG", quality=85)
                                print(f"SUCCESS - saved {image_src} - as {file_path}")
                            except Exception as e:
                                print(f"ERROR - Could not save {image_src} - as {file_path}")

                post['responses'].append(response)
            posts.append(post)
    except:
        print(f"ERROR - Could not download {day_url}")

# sadly github only allows files of 100 MB. We'll need to split up the posts
split_posts = np.array_split(posts, 4)

for i in range(len(split_posts)):
    jsonString = json.dumps(split_posts[i].tolist())
    jsonFile = open("posts" + str(i) + ".json", "w")
    jsonFile.write(jsonString)
    jsonFile.close()
