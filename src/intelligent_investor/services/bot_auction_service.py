# -----------------------------------------------------------------------------
# Copyright (c) 2025 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from datetime import date

from sqlalchemy.exc import SQLAlchemyError

from intelligent_investor.core.log import LoggerManager
from intelligent_investor.db.session import db_manager
from intelligent_investor.dtos.bot_auction import BotAuctionDTO
from intelligent_investor.models.bot_auction import BotAuctionDAO

logger = LoggerManager.get_logger(name="BotAuctionService")


class BotAuctionService:
    """
    Service layer for BotAuction CRUD operations.

    All persistence is handled via BotAuctionDAO internally.
    Callers interact exclusively with BotAuctionDTO objects.
    """

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create(self, auction: BotAuctionDTO) -> BotAuctionDTO:
        """
        Persist a new auction entry and return the saved DTO (with populated id).

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Creating auction settlement={auction.settlement_date}")
        try:
            with db_manager.get_session() as session:
                dao = BotAuctionDAO(**auction.model_dump(exclude={"id"}))
                session.add(dao)
                session.flush()
                result = BotAuctionDTO.model_validate(dao)
            logger.info(f"Auction created: id={result.id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to create auction: {e}")
            raise

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_by_id(self, auction_id: int) -> BotAuctionDTO | None:
        """Return the auction with the given id, or None if not found."""
        logger.info(f"Fetching auction id={auction_id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BotAuctionDAO).filter_by(id=auction_id).first()
                return BotAuctionDTO.model_validate(dao) if dao is not None else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch auction id={auction_id}: {e}")
            raise

    def list_upcoming(self) -> list[BotAuctionDTO]:
        """
        Return all auctions whose settlement_date >= today, ordered by settlement_date.
        Past auctions are excluded.
        """
        logger.info("Listing upcoming auctions")
        today = date.today()
        try:
            with db_manager.get_session() as session:
                daos = (
                    session.query(BotAuctionDAO)
                    .filter(BotAuctionDAO.settlement_date >= today)
                    .order_by(BotAuctionDAO.settlement_date)
                    .all()
                )
                return [BotAuctionDTO.model_validate(dao) for dao in daos]
        except SQLAlchemyError as e:
            logger.error(f"Failed to list upcoming auctions: {e}")
            raise

    def list_all(self) -> list[BotAuctionDTO]:
        """Return all auction entries ordered by settlement_date."""
        logger.info("Listing all auctions")
        try:
            with db_manager.get_session() as session:
                daos = (
                    session.query(BotAuctionDAO)
                    .order_by(BotAuctionDAO.settlement_date)
                    .all()
                )
                return [BotAuctionDTO.model_validate(dao) for dao in daos]
        except SQLAlchemyError as e:
            logger.error(f"Failed to list auctions: {e}")
            raise

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, auction: BotAuctionDTO) -> BotAuctionDTO:
        """
        Update an existing auction entry identified by auction.id.

        Raises:
            ValueError: if auction.id is None or the record does not exist.
            SQLAlchemyError: on any database failure.
        """
        if auction.id is None:
            raise ValueError("Cannot update an auction without an id")
        logger.info(f"Updating auction id={auction.id}")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BotAuctionDAO).filter_by(id=auction.id).first()
                if dao is None:
                    raise ValueError(f"Auction id={auction.id} not found")
                for key, value in auction.model_dump(exclude={"id"}).items():
                    setattr(dao, key, value)
                session.flush()
                result = BotAuctionDTO.model_validate(dao)
            logger.info(f"Auction updated: id={result.id}")
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to update auction id={auction.id}: {e}")
            raise

    # ------------------------------------------------------------------
    # Delete
    # ------------------------------------------------------------------

    def delete(self, auction_id: int) -> bool:
        """
        Delete the auction with the given id.

        Returns True if a record was deleted, False if it did not exist.

        Raises:
            SQLAlchemyError: on any database failure.
        """
        logger.info(f"Deleting auction id={auction_id}")
        try:
            with db_manager.get_session() as session:
                count = session.query(BotAuctionDAO).filter_by(id=auction_id).delete(
                    synchronize_session=False
                )
            deleted = count > 0
            if deleted:
                logger.info(f"Auction deleted: id={auction_id}")
            else:
                logger.warning(f"Auction id={auction_id} not found — nothing deleted")
            return deleted
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete auction id={auction_id}: {e}")
            raise
