from scrapely import Scraper

def create_and_dump_template(training_url, template_out="twitter_profile.tpl"):
	s = Scraper()
	data = {
		"description": "Dog lover. Tech lead on HG Memex team. Creator of PunkSPIDER. Open source developer. Distributed computing fan and security researcher.",
		"location": "Concord, NC",
		"website": "hyperiongray.com",
		"twitter.screenName": "DotSlashPunk",
		"twitter.joinedDate": "Joined April 2009",
		"twitter.tweetCount": "601",
		"twitter.followingCount": "119",
		"twitter.followerCount": "3162",
		"twitter.favoriteCount": "777",
		"twitter.listCount": "2"
	}

	s.train(training_url, data)
	f = open(template_out, "w")
	s.tofile(f)

if __name__ == "__main__":
	create_and_dump_template("https://twitter.com/DotSlashPunk")
