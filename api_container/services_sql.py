from typing import Optional, List, Dict
from lib.utils import get_actual_time
from sqlalchemy import create_engine, MetaData, Table, Column, String
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from lib.utils import get_engine
import logging as logger
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

HOUR = 60 * 60
MINUTE = 60
MILLISECOND = 1_000

# TODO: (General) -> Create tests for each method && add the required checks in each method

class Services:
    """
    Services class that stores data in a db through sqlalchemy
    Fields:
    - id: int (unique) [pk]
    - service_name (str): The name of the service
    - provider_username (str): The username of the account that provides the service
    - description (str): The description of the service
    - created_at (datetime): The date when the service was created
    - category (str): The category of the service
    - price (float): The price of the service
    - hidden (bool): If the service is hidden or not
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
                Column('uuid', UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()")),
                Column('service_name', String),
                Column('provider_username', String),
                Column('description', String),
                Column('created_at', String),
                Column('category', String),
                Column('price', String),
                Column('hidden', String)
            )
            metadata.create_all(self.engine)
            session.commit()

    def insert(self, service_name: str, provider_username: str, description: Optional[str], category: str, price: str) -> Optional[str]:
        with Session(self.engine) as session:
            try:
                query = self.services.insert().values(
                    service_name=service_name,
                    provider_username=provider_username,
                    description=description,
                    created_at=get_actual_time(),
                    category=category,
                    price=price,
                    hidden=False
                ).returning(self.services.c.uuid)
                result = session.execute(query)
                session.commit()
                inserted_id = result.scalar() # TODO: Check if this is the correct way to get the inserted id
                return inserted_id
            except IntegrityError as e:
                logger.error(f"IntegrityError: {e}")
                session.rollback()
                return None
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return None

    def get(self, uuid: str) -> Optional[dict]:
        try:
            with self.engine.connect() as connection:
                connection.execution_options(isolation_level="AUTOCOMMIT")
                query = self.services.select().where(self.services.c.uuid == uuid)
                result = connection.execute(query)
                service = result.fetchone()
                if service is None:
                    return None
                return service._asdict()
        except SQLAlchemyError as e:
            logger.error(f"SQLAlchemyError: {e}")
            return None
    
    def delete(self, uuid: str) -> bool:
        with Session(self.engine) as session:
            try:
                query = self.services.delete().where(self.services.c.uuid == uuid)
                session.execute(query)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
        return True
    
    def update(self, uuid: str, data: dict) -> bool:
        with Session(self.engine) as session:
            try:
                query = self.services.update().where(self.services.c.uuid == uuid).values(**data)
                session.execute(query)
                session.commit()
            except SQLAlchemyError as e:
                logger.error(f"SQLAlchemyError: {e}")
                session.rollback()
                return False
        return True

