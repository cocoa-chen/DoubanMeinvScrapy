# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Field,Item



class DoubanmeinvItem(Item):
    # define the fields for your item here like:
    feedId = Field()         #feedId
    userId = Field()         #用户id
    createOn = Field()       #创建时间
    title = Field()          #feedTitle
    thumbUrl = Field()       #feed缩略图url
    href = Field()           #feed链接
    description = Field()    #feed简介
    pics = Field()           #feed的图片列表
    userInfo = Field()       #用户信息

class PicItem(Item):
    feedId = Field()
    picUrl = Field()

class UserItem(Item):
    userId = Field()         #用户id
    name = Field()           #用户name
    avatar = Field()         #用户头像
    homePage = Field()       #用户主页url
    feeds = Field()          #用户feed相册列表

class UserFeed(Item):
    userId = Field()         #用户id
    feedId = Field()         #用户图片
    thumbPic = Field()       #缩略图
    title = Field()          #标题
