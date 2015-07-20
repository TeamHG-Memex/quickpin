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


class Post(Base):
    ''' Data model for a social media post. '''

    __tablename__ = 'post'

    id = Column(Integer, primary_key=True)
    content = Column(Text)
    post_date = Column(DateTime)
    post_date_is_exact = Column(Boolean)

    # Each post has 1 author.
    author_id = Column(
        Integer,
        ForeignKey('profile.id', name='fk_post_author'),
        nullable=False
    )

    # A post has 0-n file attachments.
    attachments = relationship(
        'File',
        backref='post',
        cascade='all,delete-orphan'
    )

    def __init__(self, content, post_date, post_date_is_exact):
        ''' Constructor. '''

        self.content = content

        if isinstance(post_date, datetime):
            self.post_date = post_date
        else:
            self.post_date = dateutil.parser.parse(post_date)

        self.post_date_is_exact = post_date_is_exact
