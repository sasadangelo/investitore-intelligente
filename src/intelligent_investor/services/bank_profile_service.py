# -----------------------------------------------------------------------------
# Copyright (c) 2026 Salvatore D'Angelo, Code4Projects
# Licensed under the MIT License. See LICENSE.md for details.
# -----------------------------------------------------------------------------
from sqlalchemy.exc import SQLAlchemyError

from intelligent_investor.core.log import LoggerManager
from intelligent_investor.db.session import db_manager
from intelligent_investor.dtos.bank_profile import BankCommissionDTO, BankProfileDTO
from intelligent_investor.models.bank_profile import BankCommissionDAO, BankProfileDAO

logger = LoggerManager.get_logger(name="BankProfileService")


class BankProfileService:
    """
    Service layer for BankProfile and BankCommission CRUD operations.

    Key lookup method: resolve_commission(profile_id, venue, days)
    Returns the best-matching BankCommissionDTO for a given BOT duration.
    """

    # ------------------------------------------------------------------
    # BankProfile CRUD
    # ------------------------------------------------------------------

    def create_profile(self, profile: BankProfileDTO) -> BankProfileDTO:
        logger.info(f"Creating bank profile: {profile.bank_name} — {profile.profile_name}")
        try:
            with db_manager.get_session() as session:
                dao = BankProfileDAO(
                    bank_name=profile.bank_name,
                    profile_name=profile.profile_name,
                    notes=profile.notes,
                )
                session.add(dao)
                session.flush()
                result = BankProfileDTO.model_validate(dao)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to create bank profile: {e}")
            raise

    def get_profile(self, profile_id: int) -> BankProfileDTO | None:
        try:
            with db_manager.get_session() as session:
                dao = session.query(BankProfileDAO).filter_by(id=profile_id).first()
                return BankProfileDTO.model_validate(dao) if dao else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch bank profile id={profile_id}: {e}")
            raise

    def list_profiles(self) -> list[BankProfileDTO]:
        try:
            with db_manager.get_session() as session:
                daos = (
                    session.query(BankProfileDAO)
                    .order_by(BankProfileDAO.bank_name, BankProfileDAO.profile_name)
                    .all()
                )
                return [BankProfileDTO.model_validate(d) for d in daos]
        except SQLAlchemyError as e:
            logger.error(f"Failed to list bank profiles: {e}")
            raise

    def update_profile(self, profile: BankProfileDTO) -> BankProfileDTO:
        if profile.id is None:
            raise ValueError("Cannot update a profile without an id")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BankProfileDAO).filter_by(id=profile.id).first()
                if dao is None:
                    raise ValueError(f"BankProfile id={profile.id} not found")
                dao.bank_name = profile.bank_name
                dao.profile_name = profile.profile_name
                dao.notes = profile.notes
                session.flush()
                result = BankProfileDTO.model_validate(dao)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to update bank profile id={profile.id}: {e}")
            raise

    def delete_profile(self, profile_id: int) -> bool:
        try:
            with db_manager.get_session() as session:
                count = session.query(BankProfileDAO).filter_by(id=profile_id).delete(
                    synchronize_session=False
                )
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete bank profile id={profile_id}: {e}")
            raise

    # ------------------------------------------------------------------
    # BankCommission CRUD
    # ------------------------------------------------------------------

    def create_commission(self, commission: BankCommissionDTO) -> BankCommissionDTO:
        try:
            with db_manager.get_session() as session:
                dao = BankCommissionDAO(**commission.model_dump(exclude={"id"}))
                session.add(dao)
                session.flush()
                result = BankCommissionDTO.model_validate(dao)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to create commission: {e}")
            raise

    def get_commission(self, commission_id: int) -> BankCommissionDTO | None:
        try:
            with db_manager.get_session() as session:
                dao = session.query(BankCommissionDAO).filter_by(id=commission_id).first()
                return BankCommissionDTO.model_validate(dao) if dao else None
        except SQLAlchemyError as e:
            logger.error(f"Failed to fetch commission id={commission_id}: {e}")
            raise

    def list_commissions(self, profile_id: int) -> list[BankCommissionDTO]:
        """Return all commission rows for a given profile, ordered by venue then days_min."""
        try:
            with db_manager.get_session() as session:
                daos = (
                    session.query(BankCommissionDAO)
                    .filter_by(profile_id=profile_id)
                    .order_by(BankCommissionDAO.venue, BankCommissionDAO.days_min)
                    .all()
                )
                return [BankCommissionDTO.model_validate(d) for d in daos]
        except SQLAlchemyError as e:
            logger.error(f"Failed to list commissions for profile id={profile_id}: {e}")
            raise

    def update_commission(self, commission: BankCommissionDTO) -> BankCommissionDTO:
        if commission.id is None:
            raise ValueError("Cannot update a commission without an id")
        try:
            with db_manager.get_session() as session:
                dao = session.query(BankCommissionDAO).filter_by(id=commission.id).first()
                if dao is None:
                    raise ValueError(f"BankCommission id={commission.id} not found")
                for key, value in commission.model_dump(exclude={"id"}).items():
                    setattr(dao, key, value)
                session.flush()
                result = BankCommissionDTO.model_validate(dao)
            return result
        except SQLAlchemyError as e:
            logger.error(f"Failed to update commission id={commission.id}: {e}")
            raise

    def delete_commission(self, commission_id: int) -> bool:
        try:
            with db_manager.get_session() as session:
                count = session.query(BankCommissionDAO).filter_by(id=commission_id).delete(
                    synchronize_session=False
                )
            return count > 0
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete commission id={commission_id}: {e}")
            raise

    # ------------------------------------------------------------------
    # Commission resolution (used by the calculator)
    # ------------------------------------------------------------------

    def resolve_commission(
        self,
        profile_id: int,
        venue: str,
        days: int | None,
    ) -> BankCommissionDTO | None:
        """
        Find the best-matching commission row for the given profile, venue and days.

        Lookup order:
          1. Exact days-range match for the given venue
          2. Row with duration_type='any' (days_min=None, days_max=None) for the given venue
          3. None — caller should leave fields empty
        """
        rows = self.list_commissions(profile_id)
        venue_rows = [r for r in rows if r.venue == venue]

        # Step 1: exact days-range match
        if days is not None:
            for row in venue_rows:
                if row.days_min is not None or row.days_max is not None:
                    if row.matches_days(days):
                        return row

        # Step 2: fallback to "any" row
        for row in venue_rows:
            if row.days_min is None and row.days_max is None:
                return row

        return None

    # ------------------------------------------------------------------
    # JSON-serialisable data for the calculator JS
    # ------------------------------------------------------------------

    def profiles_with_commissions_json(self) -> list[dict]:
        """
        Return all profiles with their commission rows as plain dicts,
        ready to be embedded as JSON in the calculator template.
        """
        profiles = self.list_profiles()
        result = []
        for p in profiles:
            commissions = self.list_commissions(p.id)
            result.append({
                "id": p.id,
                "display_name": p.display_name,
                "info_url": p.info_url,
                "commissions": [c.model_dump() for c in commissions],
            })
        return result
