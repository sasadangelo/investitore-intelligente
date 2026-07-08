# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from intelligent_investor.db.session import db_manager
from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos import BondDTO
from intelligent_investor.models.bond import BondDAO

logger = LoggerManager.get_logger("BondService")


class BondService:
    """
    Service layer for Bond CRUD operations.

    All persistence is handled via BondDAO internally.
    Callers interact exclusively with BondDTO objects.
    """

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(self, bond: BondDTO) -> BondDTO:
        """
        Persist a new Bond record and return the saved DTO (with populated id).

        Raises:
            ValueError: if a bond with the same ISIN already exists.
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Creating bond ISIN={bond.isin}")
        try:
            with db_manager.get_session() as session:
                existing = session.query(BondDAO).filter_by(isin=bond.isin).first()
                if existing is not None:
                    raise ValueError(f"Bond with ISIN '{bond.isin}' already exists (id={existing.id})")

                dao = BondDAO(**bond.model_dump(exclude={"id"}))
                session.add(dao)
                session.flush()  # populate dao.id before commit
                result = BondDTO.model_validate(dao)
            logger.info(f"Bond created: id={result.id}, ISIN={result.isin}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to create bond ISIN={bond.isin}: {e}")
            raise

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_by_id(self, bond_id: int) -> BondDTO | None:
        """
        Return the Bond with the given id, or None if not found.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Fetching bond id={bond_id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondDAO).filter_by(id=bond_id).first()
                return BondDTO.model_validate(dao) if dao is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch bond id={bond_id}: {e}")
            raise

    def get_by_isin(self, isin: str) -> BondDTO | None:
        """
        Return the Bond with the given ISIN, or None if not found.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Fetching bond ISIN={isin}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondDAO).filter_by(isin=isin).first()
                return BondDTO.model_validate(dao) if dao is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch bond ISIN={isin}: {e}")
            raise

    def list_all(self) -> list[BondDTO]:
        """
        Return all Bond records.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info("Listing all bonds")
        try:
            with db_manager.get_session() as session:
                daos = session.query(BondDAO).all()
                return [BondDTO.model_validate(dao) for dao in daos]
        except SQLAlchemyError as e:
            logger.error(f"Failed to list bonds: {e}")
            raise

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, bond: BondDTO) -> BondDTO:
        """
        Update an existing Bond record identified by bond.id.

        All mutable fields are replaced with the values from the supplied DTO.

        Raises:
            ValueError: if bond.id is None or the record does not exist.
            SQLAlchemyError: on any database failure.
        """
        if bond.id is None:
            raise ValueError("Cannot update a bond without an id")
        logger.info(f"Updating bond id={bond.id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondDAO).filter_by(id=bond.id).first()
                if dao is None:
                    raise ValueError(f"Bond id={bond.id} not found")
                _apply_dto_to_dao(bond, dao)
                session.flush()
                result = BondDTO.model_validate(dao)
            logger.info(f"Bond updated: id={result.id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to update bond id={bond.id}: {e}")
            raise

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, bond_id: int) -> bool:
        """
        Delete the Bond with the given id.

        Returns True if a record was deleted, False if it did not exist.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Deleting bond id={bond_id}")
        try:
            with db_manager.get_session() as session:
                count = session.query(BondDAO).filter_by(id=bond_id).delete(synchronize_session=False)
            deleted = count > 0
            if deleted:
                logger.info(f"Bond deleted: id={bond_id}")
            else:
                logger.warning(f"Bond id={bond_id} not found — nothing deleted")
            return deleted
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete bond id={bond_id}: {e}")
            raise

    def delete_expired(self) -> int:
        """
        Delete all bonds whose maturity_date is strictly before today.

        Returns the number of deleted records.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        today = date.today()
        logger.info(f"Deleting bonds expired before {today}")
        try:
            with db_manager.get_session() as session:
                count = (
                    session.query(BondDAO)
                    .filter(BondDAO.maturity_date < today)
                    .delete(synchronize_session=False)
                )
            logger.info(f"Deleted {count} expired bond(s)")
            return count
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete expired bonds: {e}")
            raise


# ------------------------------------------------------------------
# Private helpers (not exported)
# ------------------------------------------------------------------

def _apply_dto_to_dao(dto: BondDTO, dao: BondDAO) -> None:
    """Overwrite all mutable fields of an existing BondDAO with values from a BondDTO."""
    for key, value in dto.model_dump(exclude={"id"}).items():
        setattr(dao, key, value)
