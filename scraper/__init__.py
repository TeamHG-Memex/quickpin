import scrapely
import requests
from scrapy.selector import Selector
from scrapy.http import HtmlResponse
from html2text import html2text

class Scraper(scrapely.Scraper):

	@classmethod
	def load(cls, path):
		""" Load Scraper from path """
		with open(path, "rb") as f:
			return cls.fromfile(f)

	def extract(self, username):
		""" Extract data from scrapy.Response """

		self.twitter_base = "https://twitter.com/"

		url = self.twitter_base + username
		r = requests.get(url)
		body=r.text
		response = HtmlResponse(url=url, body=body, encoding=r.encoding)
		page = scrapely.HtmlPage(response.url, response.headers, body)
		scrapely_stuff = self.scrape_page(page)[0]
		for k,v in scrapely_stuff.iteritems():
			scrapely_stuff[k] = v[0].strip()

		scraped_info = scrapely_stuff

		if "username" not in scraped_info and "twitter.screenName" in scraped_info:
			scraped_info['username'] = scraped_info['twitter.screenName']

		if "twitter.followerCount" not in scraped_info:
			#id('page-container')/x:div[1]/x:div/x:div[2]/x:div/x:div/x:div[2]/x:div/x:div/x:ul/x:li[3]/x:a/x:span[2]
			profile_values = Selector(response=response).xpath('//span[contains(@class, "ProfileNav-value")]/text()').extract()
			try:
				followerCount=profile_values[2]
			except:
				#followers count doesn't show up if it's 0 in twitter
				followerCount=0

			if followerCount:
				scraped_info["twitter.followerCount"] = followerCount

		tweets_raw = Selector(response=response).xpath("//*[contains(concat(' ', @class, ' '), ' ProfileTweet-text')]").extract()
		tweets_text = [html2text(raw_tweet).replace("\n", " ").replace("\r", " ") for raw_tweet in tweets_raw]

		avatar_url_raw = Selector(response=response).xpath('//a[contains(@class, "ProfileAvatar-container")]/@href').extract()
		print avatar_url_raw
		avatar_url = avatar_url_raw[0]
		scraped_info["imageUrl"] = avatar_url

		scraped_info["twitter.tweets.raw"] = [tweet.replace("\n", " ").replace("\r"," ") for tweet in tweets_raw]
		scraped_info["twitter.tweets.text"] = tweets_text

		self.media_url = self.twitter_base + username + "/media"
		r = requests.get(self.media_url)

		response = HtmlResponse(url=url, body=r.text, encoding=r.encoding)
		img_urls = Selector(response=response).xpath("//*[contains(concat(' ', @class, ' '), 'TwitterPhoto-mediaSource')]/@src").extract()
		scraped_info["images"] = img_urls

		if "followingCount" in scraped_info:
			scraped_info["followingCount"] = scraped_info["followingCount"].lower().replace("k", "000").replace("m", "000000").replace("b", "000000000").replace(".", "")

		if "twitter.followerCount" in scraped_info:
			scraped_info["twitter.followerCount"] = scraped_info["twitter.followerCount"].lower().replace("k", "000").replace("m", "000000").replace("b", "000000000").replace(".", "")

		if "tweetCount" in scraped_info:
			scraped_info["tweetCount"] = scraped_info["tweetCount"].lower().replace("k", "000").replace("m", "000000").replace("b", "000000000").replace(".", "")

		if "listCount" in scraped_info:
			scraped_info["listCount"] = scraped_info["listCount"].lower().replace("k", "000").replace("m", "000000").replace("b", "000000000").replace(".", "")

		if "favoriteCount" in scraped_info:
			scraped_info["favoriteCount"] = scraped_info["favoriteCount"].lower().replace("k", "000").replace("m", "000000").replace("b", "000000000").replace(".", "")

		return scraped_info

if __name__ == "__main__":
	import json

	scraper = Scraper.load("twitter_profile.tpl")

	extracted = scraper.extract("mehaase")
	print extracted["followerCount"]
	print json.dumps(extracted, sort_keys=True, indent=4, separators=(',', ': '))
