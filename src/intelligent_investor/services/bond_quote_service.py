# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from sqlalchemy.exc import SQLAlchemyError

from intelligent_investor.db.session import db_manager
from intelligent_investor.core.log import LoggerManager
from intelligent_investor.dtos import BondQuoteDTO
from intelligent_investor.models.bond_quotes import BondQuoteDAO

logger = LoggerManager.get_logger("BondQuoteService")


class BondQuoteService:
    """
    Service layer for BondQuote CRUD operations.

    All persistence is handled via BondQuoteDAO internally.
    Callers interact exclusively with BondQuoteDTO objects.
    """

    # ------------------------------------------------------------------
    # Create / Upsert
    # ------------------------------------------------------------------

    def create(self, quote: BondQuoteDTO) -> BondQuoteDTO:
        """
        Persist a new BondQuote record and return the saved DTO (with populated id).

        Because each bond has at most one current quote (unique constraint on bond_id),
        this will raise IntegrityError if a quote for the same bond already exists.
        Use upsert() to replace an existing quote.

        Raises:
            ValueError: if a quote for that bond_id already exists.
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Creating quote for bond_id={quote.bond_id}")
        try:
            with db_manager.get_session() as session:
                existing = session.query(BondQuoteDAO).filter_by(bond_id=quote.bond_id).first()
                if existing is not None:
                    raise ValueError(
                        f"Quote for bond_id={quote.bond_id} already exists (id={existing.id}). "
                        "Use upsert() to replace it."
                    )
                dao = BondQuoteDAO(**_dto_fields(quote))
                session.add(dao)
                session.flush()
                result = BondQuoteDTO.model_validate(dao)
            logger.info(f"Quote created: id={result.id}, bond_id={result.bond_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to create quote bond_id={quote.bond_id}: {e}")
            raise

    def upsert(self, quote: BondQuoteDTO) -> BondQuoteDTO:
        """
        Insert a new quote or replace the existing one for the same bond_id.

        Returns the saved DTO (with populated id).

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Upserting quote for bond_id={quote.bond_id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondQuoteDAO).filter_by(bond_id=quote.bond_id).first()
                if dao is None:
                    dao = BondQuoteDAO(**_dto_fields(quote))
                    session.add(dao)
                else:
                    _apply_dto_to_dao(quote, dao)
                session.flush()
                result = BondQuoteDTO.model_validate(dao)
            logger.info(f"Quote upserted: id={result.id}, bond_id={result.bond_id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to upsert quote bond_id={quote.bond_id}: {e}")
            raise

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_by_id(self, quote_id: int) -> BondQuoteDTO | None:
        """
        Return the BondQuote with the given id, or None if not found.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Fetching quote id={quote_id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondQuoteDAO).filter_by(id=quote_id).first()
                return BondQuoteDTO.model_validate(dao) if dao is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch quote id={quote_id}: {e}")
            raise

    def get_by_bond_id(self, bond_id: int) -> BondQuoteDTO | None:
        """
        Return the current quote for a given bond_id, or None if absent.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Fetching quote for bond_id={bond_id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondQuoteDAO).filter_by(bond_id=bond_id).first()
                return BondQuoteDTO.model_validate(dao) if dao is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch quote bond_id={bond_id}: {e}")
            raise

    def list_all(self) -> list[BondQuoteDTO]:
        """
        Return all BondQuote records.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info("Listing all bond quotes")
        try:
            with db_manager.get_session() as session:
                daos = session.query(BondQuoteDAO).all()
                return [BondQuoteDTO.model_validate(dao) for dao in daos]
        except SQLAlchemyError as e:
            logger.error(f"Failed to list bond quotes: {e}")
            raise

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, quote: BondQuoteDTO) -> BondQuoteDTO:
        """
        Update an existing BondQuote record identified by quote.id.

        Raises:
            ValueError: if quote.id is None or the record does not exist.
            SQLAlchemyError: on any database failure.
        """
        if quote.id is None:
            raise ValueError("Cannot update a bond quote without an id")
        logger.info(f"Updating quote id={quote.id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BondQuoteDAO).filter_by(id=quote.id).first()
                if dao is None:
                    raise ValueError(f"BondQuote id={quote.id} not found")
                _apply_dto_to_dao(quote, dao)
                session.flush()
                result = BondQuoteDTO.model_validate(dao)
            logger.info(f"Quote updated: id={result.id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to update quote id={quote.id}: {e}")
            raise

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, quote_id: int) -> bool:
        """
        Delete the BondQuote with the given id.

        Returns True if a record was deleted, False if it did not exist.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Deleting quote id={quote_id}")
        try:
            with db_manager.get_session() as session:
                count = session.query(BondQuoteDAO).filter_by(id=quote_id).delete(synchronize_session=False)
            deleted = count > 0
            if deleted:
                logger.info(f"Quote deleted: id={quote_id}")
            else:
                logger.warning(f"Quote id={quote_id} not found — nothing deleted")
            return deleted
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete quote id={quote_id}: {e}")
            raise

    def delete_by_bond_id(self, bond_id: int) -> bool:
        """
        Delete the current quote associated with the given bond_id.

        Returns True if a record was deleted, False if none existed.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Deleting quote for bond_id={bond_id}")
        try:
            with db_manager.get_session() as session:
                count = session.query(BondQuoteDAO).filter_by(bond_id=bond_id).delete(synchronize_session=False)
            deleted = count > 0
            if deleted:
                logger.info(f"Quote deleted for bond_id={bond_id}")
            else:
                logger.warning(f"No quote found for bond_id={bond_id} — nothing deleted")
            return deleted
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete quote bond_id={bond_id}: {e}")
            raise


# ------------------------------------------------------------------
# Private helpers (not exported)
# ------------------------------------------------------------------

def _dto_fields(dto: BondQuoteDTO) -> dict:
    """
    Return DTO fields as a dict ready for BondQuoteDAO construction/update.
    Renames 'date' → 'quote_date' to match the DAO column name.
    """
    data = dto.model_dump(exclude={"id"})
    data["quote_date"] = data.pop("date")
    return data


def _apply_dto_to_dao(dto: BondQuoteDTO, dao: BondQuoteDAO) -> None:
    """Overwrite all mutable fields of an existing BondQuoteDAO with values from the DTO."""
    for key, value in _dto_fields(dto).items():
        setattr(dao, key, value)
