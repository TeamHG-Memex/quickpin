from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import validates

from model import Base


class Label(Base):

    __tablename__ = 'label'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)

    def __init__(self, name):
        ''' Constructor. '''

        self.name = name

    def as_dict(self):
        ''' Return dictionary representation of this tag. '''

        return {
            'id': self.id,
            'name': self.name,
        }

    # Allow only alphanumeric and whitespace
    @validates('name')
    def validate_name(self, key, name):
        assert name.replace(' ', '').isalnum()
        return name
