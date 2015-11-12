# -*- coding: utf-8 -*-
import scrapy
import re
from DoubanMeinv.items import DoubanmeinvItem,UserItem,UserFeed
import json

import sys
reload(sys)
sys.setdefaultencoding('utf8')

class DbmeinvSpider(scrapy.Spider):
    name = "dbMeinv"
    allowed_domains = ["www.dbmeinv.com"]
    start_urls = (
        'http://www.dbmeinv.com/dbgroup/rank.htm?pager_offset=1',
        # 'http://www.dbmeinv.com/dbgroup/rank.htm?pager_offset=514',
    )
    baseUrl = 'http://www.dbmeinv.com'

    def parse(self, response):
        request = scrapy.Request(response.url,callback=self.parsePageContent)
        yield request


    #解析每一页的列表
    def parsePageContent(self, response):
        for sel in response.xpath('//div[@id="main"]//li[@class="span3"]'):
            item = DoubanmeinvItem()
            title = sel.xpath('.//div[@class="bottombar"]//a[1]/text()').extract()[0]
            #用strip()方法过滤开头的\r\n\t和空格符
            item['title'] = title.strip()
            item['thumbUrl'] = sel.xpath('.//div[@class="img_single"]//img/@src').extract()[0]
            href = sel.xpath('.//div[@class="img_single"]/a/@href').extract()[0]
            item['href'] = href
            #正则解析id
            pattern = re.compile("dbgroup/(\d*)")
            res = pattern.search(href).groups()
            item['feedId'] = res[0]
            #跳转到详情页面
            request = scrapy.Request(href,callback=self.parseMeinvDetailInfo)
            request.meta['item'] = item
            yield request
        #获取下一页并加载
        next_link = response.xpath('//div[@class="clearfix"]//li[@class="next next_page"]/a/@href')
        if(next_link):
            url = next_link.extract()[0]
            link = self.baseUrl + url
            yield scrapy.Request(link,callback=self.parsePageContent)
        # #获取上一页并加载
        # previous_link = response.xpath('//div[@class="clearfix"]//li[@class="prev previous_page"]/a/@href')
        # if(previous_link):
        #     url = previous_link.extract()[0]
        #     link = self.baseUrl + url
        #     print "请求上一页:" + link
        #     yield scrapy.Request(link,callback=self.parsePageContent)

    #解析每一个Movie的详情页面
    def parseMeinvDetailInfo(self, response):
        item = response.meta['item']
        description = response.xpath('//div[@class="panel-body markdown"]/p[1]/text()')
        if(description):
            item['description'] = description.extract()[0]
        else:
            item['description'] = ''
        #上传时间
        createOn = response.xpath('//div[@class="info"]/abbr/@title').extract()[0]
        item['createOn'] = createOn
        #用户信息
        user = UserItem()
        avatar = response.xpath('//div[@class="user-card"]/div[@class="pic"]/img/@src').extract()[0]
        name = response.xpath('//div[@class="user-card"]/div[@class="info"]//li[@class="name"]/text()').extract()[0]
        home = response.xpath('//div[@class="user-card"]/div[@class="opt"]/a[@target="_users"]/@href').extract()[0]
        user['avatar'] = avatar
        user['name'] = name
        user['homePage'] = home
        #正则解析id
        pattern = re.compile("/users/(\d*)")
        res = pattern.search(home).groups()
        user['userId'] = res[0]
        item['userId'] = res[0]
        #将item关联user
        item['userInfo'] = user
        #解析链接
        pics = []
        links = response.xpath('//div[@class="panel-body markdown"]/div[@class="topic-figure cc"]')
        if(links):
            for a in links:
                img = a.xpath('./img/@src')
                if(img):
                    picUrl = img.extract()[0]
                    pics.append(picUrl)
        #转成json字符串保存
        item['pics'] = json.dumps(list(pics))
        #跳转到用户详情页面
        request = scrapy.Request(home,callback=self.parseUserPicLists)
        request.meta['item'] = item
        yield request

    def parseUserPicLists(self,response):
        item = response.meta['item']
        user = item['userInfo']
        uls = response.xpath('//ul[@class="thumbnails"]/li[@class="span2"]')
        feeds = []
        for li in uls:
            feed = UserFeed()
            thumb = li.xpath('.//img/@src').extract()[0]
            title = li.xpath('.//img/@title').extract()[0]
            href = li.xpath('./div[1]/a/@href').extract()[0]
            feed['title'] = title
            feed['thumbPic'] = thumb
            #正则解析id
            pattern = re.compile("dbgroup/(\d*)")
            res = pattern.search(href).groups()
            feed['feedId'] = res[0]
            feed['userId'] = user['userId']
            feeds.append(feed)
        user['feeds'] = feeds
        item['userInfo'] = user
        return item