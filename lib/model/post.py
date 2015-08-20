import base64
from datetime import datetime
import dateutil.parser
import os
import re

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Float, \
                       func, Integer, String, Table, Text, UniqueConstraint
from sqlalchemy.orm import relationship

import app.config
from model import Base


file_join_post = Table(
    'file_join_post',
    Base.metadata,
    Column('file_id', Integer, ForeignKey('file.id'), primary_key=True),
    Column('post_id', Integer, ForeignKey('post.id'), primary_key=True),
)


class Post(Base):
    ''' Data model for a social media post. '''

    __tablename__ = 'post'

    id = Column(Integer, primary_key=True)
    upstream_id = Column(String(255), nullable=False)
    upstream_created = Column(DateTime)
    last_update = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    content = Column(Text)
    language = Column(String(255))
    latitude = Column(Float)
    longitude = Column(Float)
    location = Column(Text)

    # Each post has 1 author.
    author_id = Column(
        Integer,
        ForeignKey('profile.id', name='fk_post_author'),
        nullable=False
    )

    # A post has 0-n file attachments.
    attachments = relationship(
        'File',
        backref='posts',
        secondary=file_join_post
    )

    def __init__(self, author, upstream_id, upstream_created, content):
        ''' Constructor. '''

        self.author = author
        self.upstream_id = upstream_id
        self.upstream_created = upstream_created
        self.content = content
