from sqlalchemy import Column, ForeignKey, Integer, String, Text

from model import Base


class Credential(Base):
    '''
    Stores a credential for accessing a social site.

    This could be a plain old username/password for sites that we scrape, or
    it could be an API key/secret. The `public` field contains a public
    identifier, such as a username or API ID. The `secret` field contains
    the password or API secret key.

    Only one credential pair per site is allowed.
    '''

    __tablename__ = 'credential'

    id = Column(Integer, primary_key=True)
    site = Column(String(255), unique=True)
    public = Column(Text)
    secret = Column(Text)

    def __init__(self, site, public, secret):
        ''' Constructor. '''

        self.site = site
        self.public = public
        self.secret = secret
