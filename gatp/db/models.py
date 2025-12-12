from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, DATETIME
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    admin = Column(Boolean, default=False)


class Trunk(Base):
    __tablename__ = "trunks"
    name = Column(String, primary_key=True)
    allow_push = Column(Boolean, default=False)
    require_pr = Column(Boolean, default=True)
    deprecated = Column(Boolean, default=False)
    default_branch = Column(Boolean, default=False)
    sync_with = Column(Text)  # list, es. 'develop,release'


class Flow(Base):
    __tablename__ = "flows"
    name = Column(String, primary_key=True)
    prefix = Column(String, nullable=False)
    parent = Column(String, ForeignKey("trunks.name"), nullable=False)
    target = Column(String, nullable=False)  # list, es. 'develop,main'
    max_lifetime_days = Column(Integer, default=None)
    auto_delete = Column(Boolean, default=False)
    allow_push = Column(Boolean, default=False)
    require_pr = Column(Boolean, default=True)


class Bind(Base):
    __tablename__ = "binds"
    name = Column(String, primary_key=True)
    parent = Column(String, ForeignKey("trunks.name"), nullable=False)
    target = Column(String, nullable=False)
    mode = Column(String, nullable=False)
    tag = Column(Boolean, default=True)
    conflict_policy = Column(String, default="block")
    schedule = Column(String, default="on_push")


class Log(Base):
    __tablename__ = "logger"
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DATETIME, default=datetime.utcnow)
    user = Column(String)
    level = Column(String)
    message = Column(Text)
