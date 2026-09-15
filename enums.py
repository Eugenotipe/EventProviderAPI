from enum import Enum

class EventStatus(str, Enum):
    NEW = 'new'
    PUBLISHED = 'published'