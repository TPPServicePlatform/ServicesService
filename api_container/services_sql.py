from typing import Optional, List, Dict
from sqlalchemy import create_engine, MetaData, Table, Column, String
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from lib.utils import get_engine
import logging as logger
from sqlalchemy.orm import Session

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

class Services:
    """
    Services class that stores data in a db through sqlalchemy
    Fields:
    - service (str): The name of the service
    - username (str): The username of the account -> foreign key to the accounts table
    """

    def __init__(self):
        self.engine = get_engine()
        self.create_table()
        logger.getLogger('sqlalchemy.engine').setLevel(logger.DEBUG)

    def create_table(self):
        with Session(self.engine) as session:
            metadata = MetaData()
            self.services = Table(
                'services',
                metadata,
                Column('service_name', String, primary_key=True),
                Column('username', String, primary_key=True)
            )
            metadata.create_all(self.engine)
            session.commit()

    def insert(self, username: str, service_name: str) -> bool:
        with Session(self.engine) as session:
            try:
                query = self.services.insert().values(service_name=service_name, username=username)
                session.execute(query)
                session.commit()
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                session.rollback()
                return False
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
            return True

    def get(self, username: str) -> Optional[List[Dict[str, str]]]:
        try:
            with self.engine.connect() as connection:
                connection.execution_options(isolation_level="AUTOCOMMIT")
                query = self.services.select().where(self.services.c.username == username)
                result = connection.execute(query)
                services = result.fetchall()
                if services is None:
                    return None
                return [service[0] for service in services]
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError: {e}")
            return None

