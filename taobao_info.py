import re
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pyquery import PyQuery as pq
from config import *
import pymongo
#连接MonGoDB
client = pymongo.MongoClient(MONGO_URL)
db = client[MONGO_DB]
#开启phantomjs浏览器并配置config中的参数service_args（是一个无界面的浏览器）
driver = webdriver.PhantomJS(service_args=SERVICE_ARGS)
#定义一个参数判断网页是否加载完成
wait =  WebDriverWait(driver, 10)
#设置浏览器窗口大小
driver.set_window_size(1400,900)
#搜索功能
def search(keyword):
    print('正在搜索')
    try:
        driver.get('https://www.taobao.com/')
        #获取淘宝搜索输入框，浏览器代码中右键COPY>COPYSELECT得到#q，后面代码同理
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#q"))
        )
        #获取搜索确定按钮
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR,"#J_TSearchForm > div.search-button > button"))
        )
        #输入关键词
        input.send_keys(keyword)
        #点击搜索按钮
        submit.click()
        #获取搜索结果总页码
        total = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > div.total')))
        #运行函数获取商品信息
        get_products()
        #返回总页码数
        return total.text
    except TimeoutException:
        #如果加载出错，重新加载
        return search(keyword)
#定义翻页方法
def next_page(page_number):
    print('正在翻页:',page_number)
    try:
        #获取跳转页码输入框
        input = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > input"))
        )
        #获取确定跳转页按钮
        submit = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#mainsrp-pager > div > div > div > div.form > span.btn.J_Submit"))
        )
        #清空页码输入框，避免默认页面干扰
        input.clear()
        #输入跳转页码
        input.send_keys(page_number)
        #点击跳转
        submit.click()
        #加载页码高亮框内数字，以确认页面加载完成
        wait.until(EC.text_to_be_present_in_element((By.CSS_SELECTOR,'#mainsrp-pager > div > div > div > ul > li.item.active > span'),str(page_number)))
        #获取商品信息
        get_products()
    except TimeoutException:
        #如果加载出错，重新加载
        return next_page(page_number)
#获取商品信息
def get_products():
    #等待页面加载完成
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,'#mainsrp-itemlist .items .item')))
    #拿到网页源代码
    html = driver.page_source
    #解析源代码
    doc = pq(html)
    #获取item元素内容
    items = doc('#mainsrp-itemlist .items .item').items()
    #循环获取到的内容
    for item in items:
        #创建字典，定义商品信息
        product = {
            'image':item.find('.pic .img').attr('src'),
            'price':item.find('.price').text(),
            'deal':item.find('.deal-cnt').text()[:-3],
            'title':item.find('.title').text(),
            'shop':item.find('.shop').text(),
            'location':item.find('.location').text()
        }
        #储存信息到MONGODB数据库
        save_to_mongo(product)
#储存数据库方法
def save_to_mongo(result):
    try:
        if db[MONGO_TABLE].insert(result):
            print('存储到MONGODB成功',result)
    except Exception:
        print('存货到MONGODB错误',result)
def main():
    try:
        #获取总页码
        total = search(KEYWORD)
        #总页码中还有其他字符，正则取出页码数字
        total = int(re.compile('(\d+)').search(total).group(1))
        #遍历所有页码，执行翻页操作
        for i in range(2,total+1):
           next_page(i)
    except Exception:
        print('出错啦！！！')
    finally:
        #代码结束，关闭浏览器
        driver.close()
if __name__ == '__main__':
    main()
