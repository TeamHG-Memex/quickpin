import base64
from datetime import datetime
import dateutil.parser
import os
import re

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, \
                       Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

import app.config
from model import Base


SOCIAL_SITES = {
    'twitter': 'Twitter',
    'instagram': 'Instagram',
}


file_join_profile = Table(
    'file_join_profile',
    Base.metadata,
    Column('file_id', Integer, ForeignKey('file.id'), primary_key=True),
    Column('profile_id', Integer, ForeignKey('profile.id'), primary_key=True),
)


profile_join_self = Table(
    'profile_join_self',
    Base.metadata,
    Column('follower_id', Integer, ForeignKey('profile.id'), primary_key=True),
    Column('friend_id', Integer, ForeignKey('profile.id'), primary_key=True),
)


class Profile(Base):
    ''' Data model for a profile. '''

    __tablename__ = 'profile'
    __table_args__ = (
        UniqueConstraint('site', 'original_id', name='uk_site_original_id'),
    )

    id = Column(Integer, primary_key=True)
    site = Column(Enum(*SOCIAL_SITES.keys(), name='social_site'), nullable=False)
    original_id = Column(String(255), nullable=False) # ID assigned by social site
    description = Column(Text)
    post_count = Column(Integer)
    friend_count = Column(Integer)
    follower_count = Column(Integer)
    join_date = Column(DateTime)
    join_date_is_exact = Column(Boolean)
    last_update = Column(DateTime)

    # One profile has 1-n names.
    names = relationship(
        'ProfileName',
        backref='profile',
        cascade='all,delete-orphan'
    )

    # One profile has 0-n names.
    posts = relationship(
        'Post',
        backref='author',
        cascade='all,delete-orphan'
    )

    # A profile has 0-n avatar images.
    avatars = relationship(
        'File',
        secondary=file_join_profile
    )

    # A profile can follow other profiles. We use the Twitter nomenclature and
    # call this relationship "friend".
    friends = relationship(
        'Profile',
        secondary=profile_join_self,
        primaryjoin=(id==profile_join_self.c.follower_id),
        secondaryjoin=(id==profile_join_self.c.friend_id)
    )

    # A profile can be followed other profiles.
    followers = relationship(
        'Profile',
        secondary=profile_join_self,
        primaryjoin=(id==profile_join_self.c.friend_id),
        secondaryjoin=(id==profile_join_self.c.follower_id)
    )

    def __init__(self, site, original_id, name):
        ''' Constructor. '''

        self.site = site
        self.original_id = original_id
        self.last_updated = datetime.now()

        if isinstance(name, ProfileName):
            self.names.append(name)
        else:
            self.names.append(ProfileName(name))

    def site_name(self):
        ''' Human readable name for site. '''

        return SOCIAL_SITES[self.site]


class ProfileName(Base):
    ''' A name for a profile. (A profile can have many names.) '''

    __tablename__ = 'profile_name'
    __table_args__ = (
        UniqueConstraint('name', 'profile_id', name='uk_name_profile_id'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    profile_id = Column(
        Integer,
        ForeignKey('profile.id', name='fk_profile_name'),
        nullable=False
    )

    def __init__(self, name, start_date=None, end_date=None):
        ''' Constructor. '''

        self.name = name

        if start_date is not None:
            if isinstance(start_date, datetime):
                self.start_date = start_date
            else:
                self.start_date = dateutil.parser.parse(start_date)

        if end_date is not None:
            if isinstance(end_date, datetime):
                self.end_date = end_date
            else:
                self.end_date = dateutil.parser.parse(end_date)
