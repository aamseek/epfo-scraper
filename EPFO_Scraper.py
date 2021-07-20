from selenium import webdriver
from google.cloud import vision
import io
import os
import re
import glob
import string
import json
import scrapy
# import pytesseract
from scrapy_selenium import SeleniumRequest
from PIL import Image
import numpy
from scrapy.selector import Selector
from selenium.webdriver.common.keys import Keys
from PIL import ImageFilter
# from scipy.ndimage.filters import gaussian_filter
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from time import sleep
from google.protobuf.json_format import MessageToDict
from selenium.webdriver.chrome.options import Options


def get_captcha():
    # th1 = 90
    # th2 = 30
    # sig = 1.5
    # orignal = Image.open("captcha.png")
    # orignal.save("orignal.png")
    # black_and_white = orignal.convert("L")
    # black_and_white.save("black_and_white.png")
    # first_threshold = black_and_white.point(lambda p:p>th1 and 255)
    # first_threshold.save("first_threshold.png")
    #blur = numpy.array(first_threshold)
    #blurred = gaussian_filter(blur,sigma=sig)
    #blurred = Image.fromarray(blurred)
    #blurred.save('blurred.png')
    #final = blurred.point(lambda p:p>th2 and 255)
    #final = final.filter(ImageFilter.EDGE_ENHANCE_MORE)
    #final = final.filter(ImageFilter.SHARPEN)
    #final.save("final.png")
    #number = pytesseract.image_to_string(Image.open(os.path.abspath('first_threshold.png')))

    # image = r'/Users/chandrimasabharwal/scrapy_projects/EPFscraper/captcha.png'
    VisionAPIClient = vision.ImageAnnotatorClient()

    with io.open("captcha.png", 'rb') as image_file:
        content = image_file.read()

    # Send the image content to vision and stores text-related response in text
    image = vision.types.Image(content=content)
    response = VisionAPIClient.document_text_detection(image=image)

    # Converts google vision response to dictionary
    response = MessageToDict(response, preserving_proto_field_name=True)

    document = response.get('full_text_annotation')

    # to identify and compare the break object (e.g. SPACE and LINE_BREAK) obtained in API response
    breaks = vision.enums.TextAnnotation.DetectedBreak.BreakType

    # Initialising line and bounding_box
    lines = ''
    bounding_box = []

    for page in document.get('pages'):
        for block in page.get('blocks'):
            for paragraph in block.get('paragraphs'):
                for word in paragraph.get('words'):
                    for symbol in word.get('symbols'):
                        lines = lines + symbol.get('text')
                        bounding_box.append(symbol.get(
                            'bounding_box', {}).get('vertices'))

    combined = list(zip(lines, bounding_box))
    try:
        combined.sort(key = lambda x: x[1][0]['x'])
    except Exception as e:
        print("sorting not done")

    final_text = ''.join([x[0] for x in combined if x[0].isalnum()])
    print(final_text.upper())
    return final_text.upper()

def main(org_name, f_emp_name, l_emp_name, org_code="0"):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    #chrome_options.add_argument('window-size=1200x600')
    driver = webdriver.Chrome(executable_path="chromedriver.exe",chrome_options= chrome_options)
    driver.get("http://unifiedportal-epfo.epfindia.gov.in/publicPortal/no-auth/misReport/home/loadEstSearchHome")

    #get the captcha image
    driver.save_screenshot("screen.png")
    im = Image.open("screen.png")
    width, height = im.size
    print(width,height)
    topLeft_x= width/2
    topLeft_y =height/2-(height/1600)*10
    bottomRight_x =(width/2)+(width/24*35)
    bottomRight_y=height/2+height/16
    cropped_image = im.crop((topLeft_x, topLeft_y, bottomRight_x, bottomRight_y))
    cropped_image.save("captcha.png")

    #Findinf the organisation input box and inputting the organisation name
    search_input = driver.find_element_by_xpath("//input[@id='estName']")
    search_input.send_keys(org_name)

    #if organization code is given then inputting it to the website
    if org_code != "0":
        code_input= driver.find_element_by_xpath("//*[@id='estCode']")
        code_input.send_keys(org_code)

    #finding the captcha inpy box and inputting it
    captcha_input = driver.find_element_by_id('captcha')
    captcha_input.send_keys(get_captcha())

    #finding the search button and clicking it
    search_btn =  driver.find_element_by_id("searchEmployer")
    search_btn.send_keys(Keys.ENTER)
    sleep(2)

    #if the captcha OCR is wrong
    if driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div").text == "Please enter valid captcha.":
        return "Invalid Captcha"
    #if the organisation name or organization code is wrong
    if driver.find_element_by_xpath("//html/body/div/div/div[2]/div[4]/div/div[2]/div/div").text == "No details found for this criteria. Please enter valid Establishment name or code number .":
        return {"status":"fail","ERROR":"INVALID INPUT","status_code":400}

    #calculating no. of records found for the given entry
    records =driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[1]/div").text
    #if we are able to find a unique entry
    if records == "Total Records Found : 1":
        establishment_name = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr/td[2]").text
        office_name = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr/td[4]").text
        view_details = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr/td[5]/a").click()
        sleep(8)
        view_payment = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[5]/div/div[2]/div/div/a")
        sleep(5)
        view_payment.click()
        sleep(3)
        new_window = driver.window_handles[1]
        driver.switch_to_window(new_window)
        if driver.find_element_by_xpath("/html/body/div/div/div[2]/div").text == "No Payment details found for this Establishment.":
            return {"status":"success","data":"NO DETAILS FOUND","status_code":200}
        next_btn = driver.find_element_by_xpath("//*[@class='paginate_button next']")
        while next_btn:
            try:
                next_btn.click()
                next_btn = driver.find_element_by_xpath("//*[@class='paginate_button next']")
            except:
                break
        detail_row = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[1]/div/div[2]/div/table/tbody/tr[1]/td[5]/a")
        j=1
        while j:
            try:
                detail_row = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[1]/div/div[2]/div/table/tbody/tr[j]/td[5]/a")
                j=j+1
            except:
                break

        detail_row.click()
        sleep(5)
        name_search = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div/div[2]/label/input")
        name_search.send_keys(f_emp_name)

        if driver.find_element_by_xpath("/html/body/div/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div/table/tbody/tr/td").text == "No matching records found":
            return {"status":"success","data":"N0 MATCHING RECORDS FOUND","status_code":200}
        k = 1
        names = []
        employees = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div/table/tbody/tr["+str(k)+"]/td").text
        while k:
            try:
                employees = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[2]/div/div[2]/div/div/div/div[2]/div/table/tbody/tr["+str(k)+"]/td").text
                names.append(employees)
                k = k+1
            except:
                return {"status":"success", "data":names, "statis_code":200}
    #for the times we have more than one organization related to the given name
    else:
        response =[]
        i = 1
        while i:
            try:
                establishment_code = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr["+str(i)+"]/td[1]").text
                establishment_name = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr["+str(i)+"]/td[2]").text
                establishment_address = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr["+str(i)+"]/td[3]").text
                office_name = driver.find_element_by_xpath("/html/body/div/div/div[2]/div[4]/div/div[2]/div/div/div[2]/table/tbody/tr["+str(i)+"]/td[4]").text

                a_dict=  {
                    "establishment_code":establishment_code,
                    "establishment_name":establishment_name,
                    "establishment_address":establishment_address,
                    "office_name":office_name
                }
                response.append(a_dict)
                i = i+1
            except:
                try:
                    new_next= driver.find_element_by_xpath("//*[@class='paginate_button next']")
                    new_next.click()
                    i=1
                except:
                    return {"status":"success", "data":response, "statis_code":200}



