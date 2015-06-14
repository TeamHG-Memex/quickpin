from scrapely import Scraper

def create_and_dump_template(training_url, template_out="twitter_profile.tpl"):
	s = Scraper()
	data = {
		"description": "Arrogance",
		"location": "USA",
		"website": "buifamily.info/duy",
		"twitter.screenName": "khuongduybui",
		"twitter.joinedDate": "Joined August 2008",
		"twitter.tweetCount": "463",
		"twitter.followingCount": "20",
		"twitter.followerCount": "68",
		"twitter.favoriteCount": "1",
		"twitter.listCount": "3"
	}

	s.train(training_url, data)
	f = open(template_out, "w")
	s.tofile(f)

if __name__ == "__main__":
	create_and_dump_template("https://twitter.com/khuongduybui")
