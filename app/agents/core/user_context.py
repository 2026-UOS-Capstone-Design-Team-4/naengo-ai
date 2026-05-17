from sqlalchemy.orm import Session

from app.models.user import UserProfile


class UserContextBuilder:
    def build_profile_context(self, db: Session, user_id: int) -> str | None:
        profile = db.query(UserProfile).filter_by(user_id=user_id).first()
        if not profile:
            return None
        return self.build_from_profile(profile)

    def build_from_profile(self, profile: UserProfile) -> str | None:
        parts = []
        if profile.allergies:
            parts.append(f"알레르기: {', '.join(profile.allergies)}")
        if profile.disliked_ingredients:
            parts.append(f"싫어하는 재료: {', '.join(profile.disliked_ingredients)}")
        if profile.preferred_ingredients:
            parts.append(f"좋아하는 재료: {', '.join(profile.preferred_ingredients)}")
        if profile.dietary_restrictions:
            parts.append(f"식이 제한: {', '.join(profile.dietary_restrictions)}")
        if profile.taste_keywords:
            parts.append(f"선호 맛: {', '.join(profile.taste_keywords)}")
        if profile.cooking_skill:
            skill_map = {"easy": "초급", "normal": "중급", "hard": "고급"}
            skill = skill_map.get(profile.cooking_skill, profile.cooking_skill)
            parts.append(f"요리 수준: {skill}")
        if profile.preferred_cooking_time_minutes:
            parts.append(
                f"선호 조리 시간: {profile.preferred_cooking_time_minutes}분 이내"
            )
        return "\n".join(parts) if parts else None


user_context_builder = UserContextBuilder()
