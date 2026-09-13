"""
app/schemas/enums.py — shared categorical vocabularies.

Every value set here was verified directly against the source CSVs before
being locked in, rather than guessed from column names.
Using `StrEnum` (not a plain `str` + regex) makes each valid set of values
self-documenting in the OpenAPI/Swagger docs and rejects typos at the
request-validation layer instead of at the database.
"""
from enum import StrEnum


class Gender(StrEnum):
    MALE = "Male"
    FEMALE = "Female"
    NON_BINARY = "Non-Binary"


class CustomerSegment(StrEnum):
    CONSUMER = "Consumer"
    PREMIUM = "Premium"
    VIP = "VIP"
    BUSINESS = "Business"


class CustomerType(StrEnum):
    LOYAL = "Loyal"
    NEW = "New"
    RETURNING = "Returning"


class Region(StrEnum):
    CENTRAL = "Central"
    EAST = "East"
    NORTH = "North"
    SOUTH = "South"
    WEST = "West"


class OrderStatus(StrEnum):
    CANCELLED = "Cancelled"
    COMPLETED = "Completed"
    PENDING = "Pending"
    RETURNED = "Returned"


class DeliveryStatus(StrEnum):
    CANCELLED = "Cancelled"
    DELAYED = "Delayed"
    EARLY = "Early"
    ON_TIME = "On Time"


class PaymentStatus(StrEnum):
    FAILED = "Failed"
    PAID = "Paid"
    PENDING = "Pending"
    REFUNDED = "Refunded"


class PaymentMethod(StrEnum):
    BANK_TRANSFER = "Bank Transfer"
    BUY_NOW_PAY_LATER = "Buy Now Pay Later"
    CASH_ON_DELIVERY = "Cash on Delivery"
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"
    DIGITAL_WALLET = "Digital Wallet"
    PAYPAL = "PayPal"


class ShippingMethod(StrEnum):
    ECONOMY = "Economy"
    EXPRESS = "Express"
    SAME_DAY = "Same Day"
    STANDARD = "Standard"


class SalesChannel(StrEnum):
    MARKETPLACE = "Marketplace"
    MOBILE_APP = "Mobile App"
    SOCIAL_MEDIA = "Social Media"
    WEBSITE = "Website"


class MarketingChannel(StrEnum):
    AFFILIATE = "Affiliate"
    DIRECT = "Direct"
    EMAIL_MARKETING = "Email Marketing"
    FACEBOOK_ADS = "Facebook Ads"
    GOOGLE_ADS = "Google Ads"
    INSTAGRAM = "Instagram"
    ORGANIC_SEARCH = "Organic Search"
    REFERRAL = "Referral"
    TIKTOK = "TikTok"
    YOUTUBE = "YouTube"


class Currency(StrEnum):
    AED = "AED"
    AUD = "AUD"
    CAD = "CAD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    USD = "USD"


class ReviewSentiment(StrEnum):
    NEGATIVE = "Negative"
    NEUTRAL = "Neutral"
    POSITIVE = "Positive"


class ProductCategory(StrEnum):
    AUTOMOTIVE = "Automotive"
    BABY_AND_KIDS = "Baby & Kids"
    BEAUTY_AND_PERSONAL_CARE = "Beauty & Personal Care"
    BOOKS_AND_MEDIA = "Books & Media"
    ELECTRONICS = "Electronics"
    FASHION = "Fashion"
    GROCERY = "Grocery"
    HEALTH_AND_WELLNESS = "Health & Wellness"
    HOME_AND_KITCHEN = "Home & Kitchen"
    HOME_APPLIANCES = "Home Appliances"
    JEWELRY = "Jewelry"
    OFFICE_SUPPLIES = "Office Supplies"
    PET_SUPPLIES = "Pet Supplies"
    SPORTS_AND_OUTDOORS = "Sports & Outdoors"
    TOYS_AND_GAMES = "Toys & Games"
