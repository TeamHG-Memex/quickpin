from datetime import datetime
import io
import os
import re
import urllib.parse

from PIL import Image
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Table, Text
from sqlalchemy.orm import relationship

import app.config
from model import Base
from model.file import File


THUMB_SIZE = (32, 32)


class Avatar(Base):
    ''' Data model for a profile's avatar image. '''

    __tablename__ = 'avatar'

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('file.id'))
    thumb_file_id = Column(Integer, ForeignKey('file.id'))
    upstream_url = Column(Text)
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    file = relationship('File', foreign_keys=[file_id])
    thumb_file = relationship('File', foreign_keys=[thumb_file_id])

    def __init__(self, url, mime, image):
        ''' Constructor. '''

        parsed = urllib.parse.urlparse(url)
        name = os.path.basename(parsed.path)

        self.upstream_url = url
        self.file = File(name, mime, image)
        now = datetime.now()
        self.start_date = now
        self.end_date = now

        thumb_file = io.BytesIO(image)
        thumb = Image.open(thumb_file)
        # Handle files that are in palette rather than RGB mode
        if thumb.mode != 'RGB':
            thumb = thumb.convert('RGB')
        thumb.thumbnail(THUMB_SIZE)
        thumb_file.seek(0)
        thumb.save(thumb_file, format='JPEG')
        thumb_file.seek(0)
        self.thumb_file = File('thumb-{}'.format(name), mime, thumb_file.read())
