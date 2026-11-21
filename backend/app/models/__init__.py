"""Import every model here so Alembic's autogenerate sees them all."""
from app.models.base import Base
from app.models.business import BusinessProfile
from app.models.chat import ChatMessage, SupportEscalation
from app.models.destination import DestinationFeature
from app.models.document import UserDocument
from app.models.embedding import TripEmbedding
from app.models.package import PackageBooking, TravelPackage
from app.models.packing import PackingDefault, PackingItem
from app.models.group import TripCollaborator, TripFeedback, TripMatchRequest, TripRoomMessage
from app.models.refresh_token import RefreshToken
from app.models.risk import ActivityEvent, AdminAction, FraudFlag
from app.models.ticket import Ticket
from app.models.trip import Itinerary, Trip
from app.models.user import User

__all__ = [
    "ActivityEvent",
    "AdminAction",
    "Base",
    "BusinessProfile",
    "ChatMessage",
    "DestinationFeature",
    "FraudFlag",
    "Itinerary",
    "PackageBooking",
    "PackingDefault",
    "PackingItem",
    "RefreshToken",
    "SupportEscalation",
    "Ticket",
    "TravelPackage",
    "Trip",
    "TripCollaborator",
    "TripEmbedding",
    "TripFeedback",
    "TripMatchRequest",
    "TripRoomMessage",
    "User",
    "UserDocument",
]
