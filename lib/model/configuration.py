from sqlalchemy import Column, ForeignKey, Integer, String, Text

from model import Base


class Configuration(Base):
    '''
    Stores a configuration key/value pair.
    '''

    __tablename__ = 'configuration'

    id = Column(Integer, primary_key=True)
    key = Column(String(255), unique=True)
    value = Column(Text)

    def __init__(self, key, value):
        ''' Constructor. '''

        self.key = key
        self.value = value
