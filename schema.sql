--
-- PostgreSQL database dump
--

\restrict HjfJyBCe5BJ1X3AlkQ8YTTehzJYWWm3gWo5sCwhLzYNw9YHUn1vixR6GrtHmZOO

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: account_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.account_role AS ENUM (
    'ADMIN',
    'STAFF',
    'CUSTOMER'
);


ALTER TYPE public.account_role OWNER TO postgres;

--
-- Name: actor_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.actor_type AS ENUM (
    'USER',
    'ADMIN',
    'STAFF',
    'CUSTOMER'
);


ALTER TYPE public.actor_type OWNER TO postgres;

--
-- Name: booking_source; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.booking_source AS ENUM (
    'APP',
    'WEBSITE',
    'WHATSAPP',
    'FACEBOOK',
    'INSTAGRAM',
    'PHONE',
    'WALK_IN',
    'EXISTING_CUSTOMER',
    'REFERRAL',
    'B2B',
    'OFFLINE',
    'OTHER'
);


ALTER TYPE public.booking_source OWNER TO postgres;

--
-- Name: booking_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.booking_status AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED',
    'COMPLETED',
    'TENTATIVE',
    'PARTIALLY_PAID',
    'FULLY_PAID',
    'TRAVELLED',
    'ON_HOLD',
    'REFUNDED'
);


ALTER TYPE public.booking_status OWNER TO postgres;

--
-- Name: booking_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.booking_type AS ENUM (
    'TOUR_PACKAGE',
    'CUSTOM_TOUR',
    'ROOM_BOOKING'
);


ALTER TYPE public.booking_type OWNER TO postgres;

--
-- Name: customer_tour_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.customer_tour_status AS ENUM (
    'PLANNED',
    'CONFIRMED',
    'CANCELLED',
    'COMPLETED'
);


ALTER TYPE public.customer_tour_status OWNER TO postgres;

--
-- Name: discount_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.discount_type AS ENUM (
    'PERCENTAGE',
    'FIXED'
);


ALTER TYPE public.discount_type OWNER TO postgres;

--
-- Name: document_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.document_type AS ENUM (
    'ID_PROOF',
    'ADDRESS_PROOF',
    'TOUR_DOCUMENT',
    'OTHER'
);


ALTER TYPE public.document_type OWNER TO postgres;

--
-- Name: enquiry_channel; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.enquiry_channel AS ENUM (
    'WEBSITE',
    'WHATSAPP',
    'PHONE',
    'EMAIL',
    'OFFLINE',
    'ADMIN'
);


ALTER TYPE public.enquiry_channel OWNER TO postgres;

--
-- Name: enquiry_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.enquiry_status AS ENUM (
    'NEW',
    'IN_PROGRESS',
    'QUOTED',
    'CONVERTED',
    'CANCELLED',
    'CLOSED'
);


ALTER TYPE public.enquiry_status OWNER TO postgres;

--
-- Name: enquiry_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.enquiry_type AS ENUM (
    'FIXED_TOUR',
    'CUSTOM_TOUR',
    'GENERAL'
);


ALTER TYPE public.enquiry_type OWNER TO postgres;

--
-- Name: lead_source; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.lead_source AS ENUM (
    'WEBSITE',
    'WHATSAPP',
    'PHONE',
    'EMAIL',
    'OFFLINE',
    'IMPORT',
    'REFERRAL',
    'OTHER'
);


ALTER TYPE public.lead_source OWNER TO postgres;

--
-- Name: lead_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.lead_status AS ENUM (
    'NEW',
    'CONTACTED',
    'FOLLOW_UP',
    'QUALIFIED',
    'CONVERTED',
    'LOST'
);


ALTER TYPE public.lead_status OWNER TO postgres;

--
-- Name: oauth_purpose; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.oauth_purpose AS ENUM (
    'ADMIN_LOGIN',
    'CUSTOMER_LOGIN',
    'CUSTOMER_LINK'
);


ALTER TYPE public.oauth_purpose OWNER TO postgres;

--
-- Name: offer_discount_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.offer_discount_type AS ENUM (
    'PERCENTAGE',
    'FIXED'
);


ALTER TYPE public.offer_discount_type OWNER TO postgres;

--
-- Name: offer_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.offer_status AS ENUM (
    'DRAFT',
    'ACTIVE',
    'EXPIRED',
    'DISABLED'
);


ALTER TYPE public.offer_status OWNER TO postgres;

--
-- Name: payment_method; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.payment_method AS ENUM (
    'RAZORPAY',
    'UPI',
    'CASH',
    'BANK_TRANSFER',
    'CARD',
    'OFFLINE',
    'OTHER'
);


ALTER TYPE public.payment_method OWNER TO postgres;

--
-- Name: payment_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.payment_status AS ENUM (
    'PENDING',
    'SUCCESS',
    'FAILED',
    'CANCELLED',
    'REFUNDED'
);


ALTER TYPE public.payment_status OWNER TO postgres;

--
-- Name: quotation_item_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.quotation_item_type AS ENUM (
    'HOTEL',
    'TRANSPORT',
    'FLIGHT',
    'TRAIN',
    'MEAL',
    'ACTIVITY',
    'GUIDE',
    'PERMIT',
    'TRANSFER',
    'OTHER'
);


ALTER TYPE public.quotation_item_type OWNER TO postgres;

--
-- Name: quotation_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.quotation_status AS ENUM (
    'DRAFT',
    'SENT',
    'VIEWED',
    'ACCEPTED',
    'REJECTED',
    'EXPIRED',
    'CANCELLED'
);


ALTER TYPE public.quotation_status OWNER TO postgres;

--
-- Name: referral_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.referral_status AS ENUM (
    'PENDING',
    'CONVERTED',
    'REWARDED',
    'EXPIRED',
    'CANCELLED'
);


ALTER TYPE public.referral_status OWNER TO postgres;

--
-- Name: transaction_type; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.transaction_type AS ENUM (
    'PAYMENT',
    'REFUND'
);


ALTER TYPE public.transaction_type OWNER TO postgres;

--
-- Name: user_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.user_role AS ENUM (
    'ADMIN',
    'STAFF'
);


ALTER TYPE public.user_role OWNER TO postgres;

--
-- Name: vehicletype; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.vehicletype AS ENUM (
    'ANY',
    'NONE',
    'FOUR_SEATER',
    'SIX_SEATER',
    'TEMPO'
);


ALTER TYPE public.vehicletype OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: accounts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.accounts (
    account_code character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(255),
    mobile character varying(20),
    role public.account_role NOT NULL,
    last_login timestamp with time zone,
    profile_pic character varying(500),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.accounts OWNER TO postgres;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.audit_logs (
    account_id uuid,
    action character varying(50) NOT NULL,
    entity_type character varying(255) NOT NULL,
    entity_id uuid NOT NULL,
    old_values jsonb,
    new_values jsonb,
    ip_address character varying(45),
    user_agent character varying(255),
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.audit_logs OWNER TO postgres;

--
-- Name: auth_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_sessions (
    id uuid NOT NULL,
    refresh_token_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    user_agent character varying(500),
    ip_address character varying(45),
    account_id uuid
);


ALTER TABLE public.auth_sessions OWNER TO postgres;

--
-- Name: booking_costs; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booking_costs (
    booking_id uuid NOT NULL,
    cost_type character varying(50) NOT NULL,
    description character varying(200),
    vendor_id uuid,
    estimated_amount numeric(12,2) NOT NULL,
    actual_amount numeric(12,2) NOT NULL,
    paid_amount numeric(12,2) NOT NULL,
    due_amount numeric(12,2) NOT NULL,
    status character varying(30) NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.booking_costs OWNER TO postgres;

--
-- Name: booking_payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booking_payments (
    booking_id uuid NOT NULL,
    amount numeric(12,2) NOT NULL,
    currency character varying(10) NOT NULL,
    transaction_type public.transaction_type NOT NULL,
    payment_method public.payment_method NOT NULL,
    status public.payment_status NOT NULL,
    gateway character varying(50),
    transaction_id character varying(255),
    gateway_order_id character varying(255),
    gateway_payment_id character varying(255),
    gateway_signature character varying(500),
    paid_at timestamp with time zone,
    refunded_at timestamp with time zone,
    notes text,
    recorded_by_account_id uuid,
    id uuid NOT NULL,
    CONSTRAINT ck_booking_payment_amount_positive CHECK ((amount > (0)::numeric))
);


ALTER TABLE public.booking_payments OWNER TO postgres;

--
-- Name: booking_status_history; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booking_status_history (
    booking_id uuid NOT NULL,
    previous_status public.booking_status,
    status public.booking_status NOT NULL,
    changed_by_id uuid,
    notes text,
    changed_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.booking_status_history OWNER TO postgres;

--
-- Name: booking_travelers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.booking_travelers (
    booking_id uuid NOT NULL,
    full_name character varying(100) NOT NULL,
    traveler_type character varying(20) NOT NULL,
    gender character varying(20),
    date_of_birth date,
    mobile character varying(20),
    email character varying(255),
    relationship_to_customer character varying(30),
    is_primary boolean NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.booking_travelers OWNER TO postgres;

--
-- Name: bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bookings (
    booking_code character varying(20) NOT NULL,
    customer_id uuid NOT NULL,
    enquiry_id uuid,
    package_id uuid,
    variant_id uuid,
    booking_type character varying(30) NOT NULL,
    quotation_id uuid,
    source public.booking_source NOT NULL,
    sales_account_id uuid,
    status public.booking_status NOT NULL,
    departure_id uuid,
    adult_count integer NOT NULL,
    child_count integer NOT NULL,
    senior_count integer NOT NULL,
    subtotal numeric(12,2) NOT NULL,
    discount_amount numeric(12,2) NOT NULL,
    total_amount numeric(12,2) NOT NULL,
    paid_amount numeric(12,2) NOT NULL,
    due_amount numeric(12,2) NOT NULL,
    notes text,
    created_by uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.bookings OWNER TO postgres;

--
-- Name: customer_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.customer_profiles (
    account_id uuid NOT NULL,
    address character varying(255),
    emergency_contact_name character varying(100),
    emergency_contact_mobile character varying(20),
    source public.lead_source NOT NULL,
    special_discount_type public.discount_type,
    special_discount character varying(50),
    referral_code character varying(30) NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.customer_profiles OWNER TO postgres;

--
-- Name: destinations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.destinations (
    name character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    country character varying(100),
    description text,
    image_url character varying(1000),
    is_domestic boolean NOT NULL,
    is_featured boolean NOT NULL,
    is_popular boolean NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.destinations OWNER TO postgres;

--
-- Name: documents; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.documents (
    document_type public.document_type NOT NULL,
    title character varying(200) NOT NULL,
    description text,
    customer_id uuid,
    uploaded_at timestamp with time zone DEFAULT now() NOT NULL,
    file_url character varying(1000) NOT NULL,
    file_name character varying(255) NOT NULL,
    mime_type character varying(100),
    file_size bigint,
    deleted_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    uploaded_by_account_id uuid,
    deleted_by_account_id uuid
);


ALTER TABLE public.documents OWNER TO postgres;

--
-- Name: enquiries; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.enquiries (
    id uuid NOT NULL,
    enquiry_code character varying(20) NOT NULL,
    visitor_id uuid,
    customer_id uuid,
    enquiry_type public.enquiry_type NOT NULL,
    channel public.enquiry_channel NOT NULL,
    status public.enquiry_status NOT NULL,
    package_id uuid,
    variant_id uuid,
    subject character varying(200),
    message text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    room_id uuid,
    vehicle_id uuid,
    destination character varying(150),
    travel_date date,
    vehicle_type character varying(50),
    meal_plan character varying(50),
    special_requirements text,
    enquirer_name character varying(50),
    enquirer_phone character varying(20),
    travel_duration_day integer,
    travel_duration_night integer,
    adult_count integer,
    child_count integer,
    senior_count integer,
    room_count integer,
    budget_min integer,
    budget_max integer
);


ALTER TABLE public.enquiries OWNER TO postgres;

--
-- Name: expenses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.expenses (
    amount numeric(10,2) NOT NULL,
    description character varying(255),
    date timestamp with time zone NOT NULL,
    expense_category character varying(100) NOT NULL,
    payment_method character varying(100) NOT NULL,
    vendor_id uuid,
    reference character varying(255),
    attachments character varying(1000)[],
    created_by_account_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.expenses OWNER TO postgres;

--
-- Name: google_oauth_states; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.google_oauth_states (
    id uuid NOT NULL,
    state_token character varying(255) NOT NULL,
    purpose public.oauth_purpose NOT NULL,
    redirect_uri text,
    visitor_id uuid,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    is_used boolean NOT NULL
);


ALTER TABLE public.google_oauth_states OWNER TO postgres;

--
-- Name: hotels; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.hotels (
    name character varying(255) NOT NULL,
    destination character varying(255) NOT NULL,
    category character varying(50),
    address character varying(255),
    contact character varying(100),
    description text,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.hotels OWNER TO postgres;

--
-- Name: lead_activities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lead_activities (
    id uuid NOT NULL,
    channel public.enquiry_channel NOT NULL,
    activity_type character varying(50) NOT NULL,
    notes text,
    next_follow_up_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    lead_id uuid NOT NULL,
    account_id uuid
);


ALTER TABLE public.lead_activities OWNER TO postgres;

--
-- Name: leads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leads (
    id uuid NOT NULL,
    lead_code character varying(20) NOT NULL,
    full_name character varying(100) NOT NULL,
    mobile character varying(20),
    email character varying(255),
    whatsapp_opt_in boolean NOT NULL,
    lead_score integer NOT NULL,
    status public.lead_status NOT NULL,
    notes text,
    last_contacted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    enquiry_id uuid NOT NULL,
    customer_id uuid,
    visitor_id uuid,
    source public.lead_source NOT NULL
);


ALTER TABLE public.leads OWNER TO postgres;

--
-- Name: notification_campaigns; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notification_campaigns (
    notification_id uuid NOT NULL,
    recipient_id uuid NOT NULL,
    is_delivered boolean NOT NULL,
    delivered_at timestamp with time zone,
    is_read boolean NOT NULL,
    read_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.notification_campaigns OWNER TO postgres;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.notifications (
    id uuid NOT NULL,
    notification_type character varying(50) NOT NULL,
    title character varying(160) NOT NULL,
    message text NOT NULL,
    image_url character varying(1000),
    action_url character varying(1000),
    data json,
    expires_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    recipient_ids uuid[]
);


ALTER TABLE public.notifications OWNER TO postgres;

--
-- Name: otp_challenges; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.otp_challenges (
    id uuid NOT NULL,
    identifier character varying(255) NOT NULL,
    identifier_type character varying(10) NOT NULL,
    otp_hash character varying(255) NOT NULL,
    purpose character varying(30) NOT NULL,
    attempts integer NOT NULL,
    max_attempts integer NOT NULL,
    is_used boolean NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    verified_at timestamp with time zone,
    visitor_id uuid,
    customer_id uuid
);


ALTER TABLE public.otp_challenges OWNER TO postgres;

--
-- Name: COLUMN otp_challenges.identifier; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.otp_challenges.identifier IS 'Mobile number or email being verified';


--
-- Name: COLUMN otp_challenges.identifier_type; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.otp_challenges.identifier_type IS 'MOBILE or EMAIL';


--
-- Name: COLUMN otp_challenges.otp_hash; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.otp_challenges.otp_hash IS 'Bcrypt-hashed OTP, never plaintext';


--
-- Name: COLUMN otp_challenges.purpose; Type: COMMENT; Schema: public; Owner: postgres
--

COMMENT ON COLUMN public.otp_challenges.purpose IS 'LOGIN, VERIFY_MOBILE, VERIFY_EMAIL';


--
-- Name: quotation_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quotation_items (
    quotation_id uuid NOT NULL,
    item_type public.quotation_item_type NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    quantity integer NOT NULL,
    unit_price numeric(12,2) NOT NULL,
    total_price numeric(12,2) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_quotation_item_quantity_positive CHECK ((quantity > 0)),
    CONSTRAINT ck_quotation_item_total_price_non_negative CHECK ((total_price >= (0)::numeric)),
    CONSTRAINT ck_quotation_item_unit_price_non_negative CHECK ((unit_price >= (0)::numeric))
);


ALTER TABLE public.quotation_items OWNER TO postgres;

--
-- Name: quotations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.quotations (
    quotation_code character varying(50) NOT NULL,
    version integer NOT NULL,
    customer_id uuid,
    enquiry_id uuid,
    package_id uuid,
    variant_id uuid,
    tour_name character varying(255) NOT NULL,
    destination character varying(255),
    travel_date timestamp with time zone,
    return_date timestamp with time zone,
    adult_count integer NOT NULL,
    child_count integer NOT NULL,
    senior_count integer NOT NULL,
    subtotal numeric(12,2) NOT NULL,
    discount_amount numeric(12,2) NOT NULL,
    tax_amount numeric(12,2) NOT NULL,
    total_amount numeric(12,2) NOT NULL,
    valid_until timestamp with time zone,
    room_count integer NOT NULL,
    vehicle character varying(100),
    meal_plan character varying(255),
    status public.quotation_status NOT NULL,
    notes text,
    terms_and_conditions text,
    created_by_account_id uuid,
    sent_at timestamp with time zone,
    accepted_at timestamp with time zone,
    rejected_at timestamp with time zone,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_quotation_adult_count_non_negative CHECK ((adult_count >= 0)),
    CONSTRAINT ck_quotation_child_count_non_negative CHECK ((child_count >= 0)),
    CONSTRAINT ck_quotation_discount_non_negative CHECK ((discount_amount >= (0)::numeric)),
    CONSTRAINT ck_quotation_has_traveller CHECK ((((adult_count + child_count) + senior_count) > 0)),
    CONSTRAINT ck_quotation_senior_count_non_negative CHECK ((senior_count >= 0)),
    CONSTRAINT ck_quotation_subtotal_non_negative CHECK ((subtotal >= (0)::numeric)),
    CONSTRAINT ck_quotation_tax_non_negative CHECK ((tax_amount >= (0)::numeric)),
    CONSTRAINT ck_quotation_total_non_negative CHECK ((total_amount >= (0)::numeric)),
    CONSTRAINT ck_quotation_version_positive CHECK ((version > 0))
);


ALTER TABLE public.quotations OWNER TO postgres;

--
-- Name: referrals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.referrals (
    referrer_customer_id uuid NOT NULL,
    referred_customer_id uuid NOT NULL,
    status public.referral_status NOT NULL,
    reward_amount numeric(12,2),
    reward_issued_at timestamp with time zone,
    converted_at timestamp with time zone,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    id uuid NOT NULL,
    CONSTRAINT ck_referral_no_self_referral CHECK ((referrer_customer_id <> referred_customer_id))
);


ALTER TABLE public.referrals OWNER TO postgres;

--
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id uuid NOT NULL,
    package_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    rating integer NOT NULL,
    review text NOT NULL,
    is_verified boolean NOT NULL,
    is_published boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    customer_id uuid,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    review_gallery jsonb NOT NULL,
    is_active boolean NOT NULL,
    CONSTRAINT ck_reviews_rating CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- Name: room_allocations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.room_allocations (
    booking_id uuid NOT NULL,
    room_id uuid,
    room_number character varying(30),
    room_type character varying(50),
    occupant_count integer NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.room_allocations OWNER TO postgres;

--
-- Name: rooms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rooms (
    id uuid NOT NULL,
    room_number character varying(20),
    room_type character varying(50),
    capacity integer,
    price_per_night numeric(10,2),
    description text,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    hotel_id uuid
);


ALTER TABLE public.rooms OWNER TO postgres;

--
-- Name: tour_departures; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_departures (
    variant_id uuid NOT NULL,
    departure_date date NOT NULL,
    return_date date,
    total_seats integer NOT NULL,
    available_seats integer NOT NULL,
    price numeric(12,2) NOT NULL,
    id uuid NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    is_active boolean NOT NULL,
    CONSTRAINT ck_departure_available_seats_valid CHECK (((available_seats >= 0) AND (available_seats <= total_seats))),
    CONSTRAINT ck_departure_total_seats_non_negative CHECK ((total_seats >= 0))
);


ALTER TABLE public.tour_departures OWNER TO postgres;

--
-- Name: tour_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_details (
    variant_id uuid NOT NULL,
    banner jsonb NOT NULL,
    gallery jsonb NOT NULL,
    highlights jsonb NOT NULL,
    inclusions jsonb NOT NULL,
    exclusions jsonb NOT NULL,
    itinerary jsonb NOT NULL,
    route_stops jsonb NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.tour_details OWNER TO postgres;

--
-- Name: tour_offer_packages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_offer_packages (
    offer_id uuid NOT NULL,
    variant_id uuid NOT NULL,
    id uuid NOT NULL,
    is_active boolean NOT NULL
);


ALTER TABLE public.tour_offer_packages OWNER TO postgres;

--
-- Name: tour_offers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_offers (
    name character varying(255) NOT NULL,
    code character varying(100),
    status public.offer_status NOT NULL,
    description text,
    discount_type public.offer_discount_type NOT NULL,
    discount_value numeric(12,2) NOT NULL,
    max_discount_amount numeric(12,2),
    min_booking_amount numeric(12,2),
    usage_limit integer,
    per_customer_limit integer,
    usage_count integer NOT NULL,
    valid_from timestamp with time zone NOT NULL,
    valid_until timestamp with time zone NOT NULL,
    is_public boolean NOT NULL,
    is_stackable boolean NOT NULL,
    id uuid NOT NULL,
    is_active boolean NOT NULL,
    CONSTRAINT ck_tour_offer_customer_limit_positive CHECK (((per_customer_limit IS NULL) OR (per_customer_limit > 0))),
    CONSTRAINT ck_tour_offer_discount_value_non_negative CHECK ((discount_value >= (0)::numeric)),
    CONSTRAINT ck_tour_offer_usage_limit_positive CHECK (((usage_limit IS NULL) OR (usage_limit > 0))),
    CONSTRAINT ck_tour_offer_valid_dates CHECK ((valid_until > valid_from))
);


ALTER TABLE public.tour_offers OWNER TO postgres;

--
-- Name: tour_packages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_packages (
    id uuid NOT NULL,
    tour_code character varying(20) NOT NULL,
    slug character varying(200) NOT NULL,
    title character varying(200) NOT NULL,
    destination character varying(150) NOT NULL,
    type character varying(20) NOT NULL,
    description text,
    is_featured boolean NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tour_packages OWNER TO postgres;

--
-- Name: tour_variants; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_variants (
    id uuid NOT NULL,
    package_id uuid NOT NULL,
    name character varying(100) NOT NULL,
    season_name character varying(100),
    valid_from date NOT NULL,
    valid_to date NOT NULL,
    duration_days integer NOT NULL,
    duration_nights integer NOT NULL,
    base_price numeric(10,2) NOT NULL,
    is_default boolean NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    badge character varying(50),
    slug character varying(30) NOT NULL
);


ALTER TABLE public.tour_variants OWNER TO postgres;

--
-- Name: tour_wishlists; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_wishlists (
    customer_id uuid NOT NULL,
    package_id uuid NOT NULL,
    id uuid NOT NULL,
    created_at timestamp without time zone NOT NULL
);


ALTER TABLE public.tour_wishlists OWNER TO postgres;

--
-- Name: vehicle_allocations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_allocations (
    booking_id uuid NOT NULL,
    vehicle_id uuid,
    vehicle_type character varying(100),
    vehicle_name character varying(255),
    registration_number character varying(100),
    start_date timestamp with time zone,
    end_date timestamp with time zone,
    driver_name character varying(255),
    driver_mobile character varying(20),
    notes character varying(255),
    id uuid NOT NULL
);


ALTER TABLE public.vehicle_allocations OWNER TO postgres;

--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicles (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    registration_number character varying(50),
    capacity integer NOT NULL,
    price_per_day numeric(10,2) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    vehicle_type public.vehicletype NOT NULL
);


ALTER TABLE public.vehicles OWNER TO postgres;

--
-- Name: vendor_bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vendor_bookings (
    id uuid NOT NULL,
    booking_id uuid NOT NULL,
    vendor_id uuid NOT NULL,
    cost_id uuid NOT NULL
);


ALTER TABLE public.vendor_bookings OWNER TO postgres;

--
-- Name: vendor_expenses; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vendor_expenses (
    booking_id uuid NOT NULL,
    vendor_id uuid NOT NULL,
    cost_id uuid NOT NULL,
    amount numeric(12,2) NOT NULL,
    due_amount numeric(12,2) NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.vendor_expenses OWNER TO postgres;

--
-- Name: vendor_payments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vendor_payments (
    booking_cost_id uuid NOT NULL,
    amount numeric(12,2) NOT NULL,
    due_amount numeric(12,2) NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.vendor_payments OWNER TO postgres;

--
-- Name: vendors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vendors (
    vendor_code character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(50) NOT NULL,
    contact character varying(100),
    email character varying(100),
    address character varying(255),
    payment_terms character varying(100),
    status character varying(30) NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.vendors OWNER TO postgres;

--
-- Name: visitor_events; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visitor_events (
    id uuid NOT NULL,
    visitor_id uuid NOT NULL,
    session_id uuid NOT NULL,
    event_name character varying(100) NOT NULL,
    page text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.visitor_events OWNER TO postgres;

--
-- Name: visitor_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visitor_sessions (
    id uuid NOT NULL,
    visitor_id uuid NOT NULL,
    landing_page text,
    exit_page text,
    referrer text,
    utm_source character varying(100),
    utm_medium character varying(100),
    utm_campaign character varying(100),
    utm_term character varying(100),
    page_views integer NOT NULL,
    duration_seconds integer NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone
);


ALTER TABLE public.visitor_sessions OWNER TO postgres;

--
-- Name: visitors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visitors (
    id uuid NOT NULL,
    visitor_code character varying(20) NOT NULL,
    fingerprint character varying(255),
    ip_address character varying(45),
    country character varying(100),
    state character varying(100),
    city character varying(100),
    browser character varying(100),
    os character varying(100),
    device character varying(100),
    first_seen timestamp with time zone DEFAULT now() NOT NULL,
    last_seen timestamp with time zone DEFAULT now() NOT NULL,
    customer_id uuid
);


ALTER TABLE public.visitors OWNER TO postgres;

--
-- Name: accounts accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT accounts_pkey PRIMARY KEY (id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: auth_sessions auth_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_pkey PRIMARY KEY (id);


--
-- Name: booking_costs booking_costs_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_costs
    ADD CONSTRAINT booking_costs_pkey PRIMARY KEY (id);


--
-- Name: booking_payments booking_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_payments
    ADD CONSTRAINT booking_payments_pkey PRIMARY KEY (id);


--
-- Name: booking_status_history booking_status_history_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_status_history
    ADD CONSTRAINT booking_status_history_pkey PRIMARY KEY (id);


--
-- Name: booking_travelers booking_travelers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_travelers
    ADD CONSTRAINT booking_travelers_pkey PRIMARY KEY (id);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: customer_profiles customer_profiles_account_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customer_profiles
    ADD CONSTRAINT customer_profiles_account_id_key UNIQUE (account_id);


--
-- Name: customer_profiles customer_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customer_profiles
    ADD CONSTRAINT customer_profiles_pkey PRIMARY KEY (id);


--
-- Name: destinations destinations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.destinations
    ADD CONSTRAINT destinations_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (id);


--
-- Name: enquiries enquiries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_pkey PRIMARY KEY (id);


--
-- Name: expenses expenses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expenses
    ADD CONSTRAINT expenses_pkey PRIMARY KEY (id);


--
-- Name: google_oauth_states google_oauth_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_oauth_states
    ADD CONSTRAINT google_oauth_states_pkey PRIMARY KEY (id);


--
-- Name: hotels hotels_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.hotels
    ADD CONSTRAINT hotels_pkey PRIMARY KEY (id);


--
-- Name: lead_activities lead_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT lead_activities_pkey PRIMARY KEY (id);


--
-- Name: leads leads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pkey PRIMARY KEY (id);


--
-- Name: notification_campaigns notification_campaigns_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification_campaigns
    ADD CONSTRAINT notification_campaigns_pkey PRIMARY KEY (id);


--
-- Name: notifications notifications_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT notifications_pkey PRIMARY KEY (id);


--
-- Name: otp_challenges otp_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_pkey PRIMARY KEY (id);


--
-- Name: quotation_items quotation_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_pkey PRIMARY KEY (id);


--
-- Name: quotations quotations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_pkey PRIMARY KEY (id);


--
-- Name: referrals referrals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.referrals
    ADD CONSTRAINT referrals_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: room_allocations room_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_allocations
    ADD CONSTRAINT room_allocations_pkey PRIMARY KEY (id);


--
-- Name: rooms rooms_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_pkey PRIMARY KEY (id);


--
-- Name: rooms rooms_room_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_room_number_key UNIQUE (room_number);


--
-- Name: tour_departures tour_departures_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_departures
    ADD CONSTRAINT tour_departures_pkey PRIMARY KEY (id);


--
-- Name: tour_details tour_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_details
    ADD CONSTRAINT tour_details_pkey PRIMARY KEY (variant_id);


--
-- Name: tour_offer_packages tour_offer_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_offer_packages
    ADD CONSTRAINT tour_offer_packages_pkey PRIMARY KEY (id);


--
-- Name: tour_offers tour_offers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_offers
    ADD CONSTRAINT tour_offers_pkey PRIMARY KEY (id);


--
-- Name: tour_packages tour_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_packages
    ADD CONSTRAINT tour_packages_pkey PRIMARY KEY (id);


--
-- Name: tour_variants tour_variants_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_variants
    ADD CONSTRAINT tour_variants_pkey PRIMARY KEY (id);


--
-- Name: tour_wishlists tour_wishlists_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_wishlists
    ADD CONSTRAINT tour_wishlists_pkey PRIMARY KEY (id);


--
-- Name: accounts uq_accounts_email_role; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT uq_accounts_email_role UNIQUE (email, role);


--
-- Name: accounts uq_accounts_mobile_role; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.accounts
    ADD CONSTRAINT uq_accounts_mobile_role UNIQUE (mobile, role);


--
-- Name: quotations uq_quotation_enquiry_version; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT uq_quotation_enquiry_version UNIQUE (enquiry_id, version);


--
-- Name: tour_wishlists uq_tour_wishlist_customer_package; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_wishlists
    ADD CONSTRAINT uq_tour_wishlist_customer_package UNIQUE (customer_id, package_id);


--
-- Name: vehicle_allocations vehicle_allocations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_allocations
    ADD CONSTRAINT vehicle_allocations_pkey PRIMARY KEY (id);


--
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (id);


--
-- Name: vehicles vehicles_registration_number_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_registration_number_key UNIQUE (registration_number);


--
-- Name: vendor_bookings vendor_bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_bookings
    ADD CONSTRAINT vendor_bookings_pkey PRIMARY KEY (id);


--
-- Name: vendor_expenses vendor_expenses_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_expenses
    ADD CONSTRAINT vendor_expenses_pkey PRIMARY KEY (id);


--
-- Name: vendor_payments vendor_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_payments
    ADD CONSTRAINT vendor_payments_pkey PRIMARY KEY (id);


--
-- Name: vendors vendors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendors
    ADD CONSTRAINT vendors_pkey PRIMARY KEY (id);


--
-- Name: visitor_events visitor_events_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitor_events
    ADD CONSTRAINT visitor_events_pkey PRIMARY KEY (id);


--
-- Name: visitor_sessions visitor_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitor_sessions
    ADD CONSTRAINT visitor_sessions_pkey PRIMARY KEY (id);


--
-- Name: visitors visitors_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_pkey PRIMARY KEY (id);


--
-- Name: ix_accounts_account_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_accounts_account_code ON public.accounts USING btree (account_code);


--
-- Name: ix_accounts_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_accounts_email ON public.accounts USING btree (email);


--
-- Name: ix_accounts_mobile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_accounts_mobile ON public.accounts USING btree (mobile);


--
-- Name: ix_accounts_role; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_accounts_role ON public.accounts USING btree (role);


--
-- Name: ix_auth_sessions_account_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_auth_sessions_account_id ON public.auth_sessions USING btree (account_id);


--
-- Name: ix_auth_sessions_refresh_token_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_auth_sessions_refresh_token_hash ON public.auth_sessions USING btree (refresh_token_hash);


--
-- Name: ix_booking_costs_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_costs_booking_id ON public.booking_costs USING btree (booking_id);


--
-- Name: ix_booking_costs_vendor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_costs_vendor_id ON public.booking_costs USING btree (vendor_id);


--
-- Name: ix_booking_payments_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_payments_booking_id ON public.booking_payments USING btree (booking_id);


--
-- Name: ix_booking_payments_gateway_order_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_payments_gateway_order_id ON public.booking_payments USING btree (gateway_order_id);


--
-- Name: ix_booking_payments_gateway_payment_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_booking_payments_gateway_payment_id ON public.booking_payments USING btree (gateway_payment_id);


--
-- Name: ix_booking_payments_payment_method; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_payments_payment_method ON public.booking_payments USING btree (payment_method);


--
-- Name: ix_booking_payments_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_payments_status ON public.booking_payments USING btree (status);


--
-- Name: ix_booking_payments_transaction_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_payments_transaction_id ON public.booking_payments USING btree (transaction_id);


--
-- Name: ix_booking_payments_transaction_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_payments_transaction_type ON public.booking_payments USING btree (transaction_type);


--
-- Name: ix_booking_status_history_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_status_history_booking_id ON public.booking_status_history USING btree (booking_id);


--
-- Name: ix_booking_travelers_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_booking_travelers_booking_id ON public.booking_travelers USING btree (booking_id);


--
-- Name: ix_bookings_booking_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_bookings_booking_code ON public.bookings USING btree (booking_code);


--
-- Name: ix_bookings_created_by; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_created_by ON public.bookings USING btree (created_by);


--
-- Name: ix_bookings_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_customer_id ON public.bookings USING btree (customer_id);


--
-- Name: ix_bookings_departure_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_departure_id ON public.bookings USING btree (departure_id);


--
-- Name: ix_bookings_enquiry_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_bookings_enquiry_id ON public.bookings USING btree (enquiry_id);


--
-- Name: ix_bookings_quotation_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_quotation_id ON public.bookings USING btree (quotation_id);


--
-- Name: ix_bookings_sales_account_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_sales_account_id ON public.bookings USING btree (sales_account_id);


--
-- Name: ix_bookings_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_source ON public.bookings USING btree (source);


--
-- Name: ix_bookings_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_status ON public.bookings USING btree (status);


--
-- Name: ix_customer_profiles_referral_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_customer_profiles_referral_code ON public.customer_profiles USING btree (referral_code);


--
-- Name: ix_destinations_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_destinations_name ON public.destinations USING btree (name);


--
-- Name: ix_destinations_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_destinations_slug ON public.destinations USING btree (slug);


--
-- Name: ix_documents_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_customer_id ON public.documents USING btree (customer_id);


--
-- Name: ix_documents_deleted_by_account_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_deleted_by_account_id ON public.documents USING btree (deleted_by_account_id);


--
-- Name: ix_documents_document_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_document_type ON public.documents USING btree (document_type);


--
-- Name: ix_documents_uploaded_by_account_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_documents_uploaded_by_account_id ON public.documents USING btree (uploaded_by_account_id);


--
-- Name: ix_enquiries_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_enquiries_customer_id ON public.enquiries USING btree (customer_id);


--
-- Name: ix_enquiries_enquiry_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_enquiries_enquiry_code ON public.enquiries USING btree (enquiry_code);


--
-- Name: ix_enquiries_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_enquiries_package_id ON public.enquiries USING btree (package_id);


--
-- Name: ix_enquiries_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_enquiries_status ON public.enquiries USING btree (status);


--
-- Name: ix_enquiries_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_enquiries_variant_id ON public.enquiries USING btree (variant_id);


--
-- Name: ix_enquiries_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_enquiries_visitor_id ON public.enquiries USING btree (visitor_id);


--
-- Name: ix_expenses_created_by_account_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expenses_created_by_account_id ON public.expenses USING btree (created_by_account_id);


--
-- Name: ix_expenses_expense_category; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expenses_expense_category ON public.expenses USING btree (expense_category);


--
-- Name: ix_expenses_payment_method; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expenses_payment_method ON public.expenses USING btree (payment_method);


--
-- Name: ix_expenses_vendor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_expenses_vendor_id ON public.expenses USING btree (vendor_id);


--
-- Name: ix_google_oauth_states_state_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_google_oauth_states_state_token ON public.google_oauth_states USING btree (state_token);


--
-- Name: ix_google_oauth_states_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_google_oauth_states_visitor_id ON public.google_oauth_states USING btree (visitor_id);


--
-- Name: ix_lead_activities_lead_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lead_activities_lead_id ON public.lead_activities USING btree (lead_id);


--
-- Name: ix_lead_activities_next_follow_up_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lead_activities_next_follow_up_at ON public.lead_activities USING btree (next_follow_up_at);


--
-- Name: ix_leads_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_customer_id ON public.leads USING btree (customer_id);


--
-- Name: ix_leads_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_email ON public.leads USING btree (email);


--
-- Name: ix_leads_enquiry_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_leads_enquiry_id ON public.leads USING btree (enquiry_id);


--
-- Name: ix_leads_lead_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_leads_lead_code ON public.leads USING btree (lead_code);


--
-- Name: ix_leads_mobile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_mobile ON public.leads USING btree (mobile);


--
-- Name: ix_leads_source; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_source ON public.leads USING btree (source);


--
-- Name: ix_leads_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_status ON public.leads USING btree (status);


--
-- Name: ix_leads_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_visitor_id ON public.leads USING btree (visitor_id);


--
-- Name: ix_notification_campaigns_is_delivered; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_campaigns_is_delivered ON public.notification_campaigns USING btree (is_delivered);


--
-- Name: ix_notification_campaigns_is_read; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_campaigns_is_read ON public.notification_campaigns USING btree (is_read);


--
-- Name: ix_notification_campaigns_notification_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_campaigns_notification_id ON public.notification_campaigns USING btree (notification_id);


--
-- Name: ix_notification_campaigns_recipient_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notification_campaigns_recipient_id ON public.notification_campaigns USING btree (recipient_id);


--
-- Name: ix_notifications_expires_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_expires_at ON public.notifications USING btree (expires_at);


--
-- Name: ix_notifications_notification_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_notifications_notification_type ON public.notifications USING btree (notification_type);


--
-- Name: ix_otp_challenges_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_otp_challenges_customer_id ON public.otp_challenges USING btree (customer_id);


--
-- Name: ix_otp_challenges_identifier; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_otp_challenges_identifier ON public.otp_challenges USING btree (identifier);


--
-- Name: ix_otp_challenges_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_otp_challenges_visitor_id ON public.otp_challenges USING btree (visitor_id);


--
-- Name: ix_quotation_items_item_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotation_items_item_type ON public.quotation_items USING btree (item_type);


--
-- Name: ix_quotation_items_quotation_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotation_items_quotation_id ON public.quotation_items USING btree (quotation_id);


--
-- Name: ix_quotations_created_by_account_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotations_created_by_account_id ON public.quotations USING btree (created_by_account_id);


--
-- Name: ix_quotations_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotations_customer_id ON public.quotations USING btree (customer_id);


--
-- Name: ix_quotations_enquiry_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotations_enquiry_id ON public.quotations USING btree (enquiry_id);


--
-- Name: ix_quotations_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotations_package_id ON public.quotations USING btree (package_id);


--
-- Name: ix_quotations_quotation_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_quotations_quotation_code ON public.quotations USING btree (quotation_code);


--
-- Name: ix_quotations_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotations_status ON public.quotations USING btree (status);


--
-- Name: ix_quotations_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_quotations_variant_id ON public.quotations USING btree (variant_id);


--
-- Name: ix_referrals_referred_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_referrals_referred_customer_id ON public.referrals USING btree (referred_customer_id);


--
-- Name: ix_referrals_referrer_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_referrals_referrer_customer_id ON public.referrals USING btree (referrer_customer_id);


--
-- Name: ix_referrals_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_referrals_status ON public.referrals USING btree (status);


--
-- Name: ix_reviews_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_customer_id ON public.reviews USING btree (customer_id);


--
-- Name: ix_reviews_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_package_id ON public.reviews USING btree (package_id);


--
-- Name: ix_room_allocations_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_room_allocations_booking_id ON public.room_allocations USING btree (booking_id);


--
-- Name: ix_room_allocations_room_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_room_allocations_room_id ON public.room_allocations USING btree (room_id);


--
-- Name: ix_rooms_hotel_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_rooms_hotel_id ON public.rooms USING btree (hotel_id);


--
-- Name: ix_tour_departures_departure_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_departures_departure_date ON public.tour_departures USING btree (departure_date);


--
-- Name: ix_tour_departures_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_departures_variant_id ON public.tour_departures USING btree (variant_id);


--
-- Name: ix_tour_details_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_details_variant_id ON public.tour_details USING btree (variant_id);


--
-- Name: ix_tour_offer_packages_offer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_offer_packages_offer_id ON public.tour_offer_packages USING btree (offer_id);


--
-- Name: ix_tour_offer_packages_variant_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_offer_packages_variant_id ON public.tour_offer_packages USING btree (variant_id);


--
-- Name: ix_tour_offers_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_offers_code ON public.tour_offers USING btree (code);


--
-- Name: ix_tour_packages_destination; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_packages_destination ON public.tour_packages USING btree (destination);


--
-- Name: ix_tour_packages_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_packages_slug ON public.tour_packages USING btree (slug);


--
-- Name: ix_tour_packages_tour_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_packages_tour_code ON public.tour_packages USING btree (tour_code);


--
-- Name: ix_tour_variants_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_variants_package_id ON public.tour_variants USING btree (package_id);


--
-- Name: ix_tour_variants_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_variants_slug ON public.tour_variants USING btree (slug);


--
-- Name: ix_tour_wishlists_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_wishlists_customer_id ON public.tour_wishlists USING btree (customer_id);


--
-- Name: ix_tour_wishlists_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_wishlists_package_id ON public.tour_wishlists USING btree (package_id);


--
-- Name: ix_vehicle_allocations_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_allocations_booking_id ON public.vehicle_allocations USING btree (booking_id);


--
-- Name: ix_vehicle_allocations_vehicle_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_allocations_vehicle_id ON public.vehicle_allocations USING btree (vehicle_id);


--
-- Name: ix_vehicles_vehicle_type; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicles_vehicle_type ON public.vehicles USING btree (vehicle_type);


--
-- Name: ix_vendor_expenses_booking_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vendor_expenses_booking_id ON public.vendor_expenses USING btree (booking_id);


--
-- Name: ix_vendor_expenses_cost_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vendor_expenses_cost_id ON public.vendor_expenses USING btree (cost_id);


--
-- Name: ix_vendor_expenses_vendor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vendor_expenses_vendor_id ON public.vendor_expenses USING btree (vendor_id);


--
-- Name: ix_vendors_vendor_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_vendors_vendor_code ON public.vendors USING btree (vendor_code);


--
-- Name: ix_visitor_events_event_name; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_events_event_name ON public.visitor_events USING btree (event_name);


--
-- Name: ix_visitor_events_session_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_events_session_id ON public.visitor_events USING btree (session_id);


--
-- Name: ix_visitor_events_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_events_visitor_id ON public.visitor_events USING btree (visitor_id);


--
-- Name: ix_visitor_sessions_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_sessions_visitor_id ON public.visitor_sessions USING btree (visitor_id);


--
-- Name: ix_visitors_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitors_customer_id ON public.visitors USING btree (customer_id);


--
-- Name: ix_visitors_fingerprint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitors_fingerprint ON public.visitors USING btree (fingerprint);


--
-- Name: ix_visitors_visitor_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitors_visitor_code ON public.visitors USING btree (visitor_code);


--
-- Name: audit_logs audit_logs_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: auth_sessions auth_sessions_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: booking_costs booking_costs_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_costs
    ADD CONSTRAINT booking_costs_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE RESTRICT;


--
-- Name: booking_costs booking_costs_vendor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_costs
    ADD CONSTRAINT booking_costs_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES public.vendors(id) ON DELETE SET NULL;


--
-- Name: booking_payments booking_payments_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_payments
    ADD CONSTRAINT booking_payments_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: booking_payments booking_payments_recorded_by_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_payments
    ADD CONSTRAINT booking_payments_recorded_by_account_id_fkey FOREIGN KEY (recorded_by_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: booking_status_history booking_status_history_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_status_history
    ADD CONSTRAINT booking_status_history_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: booking_status_history booking_status_history_changed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_status_history
    ADD CONSTRAINT booking_status_history_changed_by_id_fkey FOREIGN KEY (changed_by_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: booking_travelers booking_travelers_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.booking_travelers
    ADD CONSTRAINT booking_travelers_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: bookings bookings_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.accounts(id) ON DELETE RESTRICT;


--
-- Name: bookings bookings_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE RESTRICT;


--
-- Name: bookings bookings_departure_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_departure_id_fkey FOREIGN KEY (departure_id) REFERENCES public.tour_departures(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_enquiry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_enquiry_id_fkey FOREIGN KEY (enquiry_id) REFERENCES public.enquiries(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_sales_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_sales_account_id_fkey FOREIGN KEY (sales_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: bookings bookings_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE SET NULL;


--
-- Name: customer_profiles customer_profiles_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customer_profiles
    ADD CONSTRAINT customer_profiles_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: documents documents_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: documents documents_deleted_by_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_deleted_by_account_id_fkey FOREIGN KEY (deleted_by_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: documents documents_uploaded_by_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_uploaded_by_account_id_fkey FOREIGN KEY (uploaded_by_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: enquiries enquiries_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: enquiries enquiries_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE SET NULL;


--
-- Name: enquiries enquiries_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id);


--
-- Name: enquiries enquiries_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE SET NULL;


--
-- Name: enquiries enquiries_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id);


--
-- Name: enquiries enquiries_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: expenses expenses_created_by_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expenses
    ADD CONSTRAINT expenses_created_by_account_id_fkey FOREIGN KEY (created_by_account_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: expenses expenses_vendor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.expenses
    ADD CONSTRAINT expenses_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES public.vendors(id) ON DELETE SET NULL;


--
-- Name: google_oauth_states google_oauth_states_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_oauth_states
    ADD CONSTRAINT google_oauth_states_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: lead_activities lead_activities_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT lead_activities_account_id_fkey FOREIGN KEY (account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: lead_activities lead_activities_lead_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT lead_activities_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.leads(id) ON DELETE CASCADE;


--
-- Name: leads leads_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: leads leads_enquiry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_enquiry_id_fkey FOREIGN KEY (enquiry_id) REFERENCES public.enquiries(id) ON DELETE CASCADE;


--
-- Name: leads leads_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: notification_campaigns notification_campaigns_notification_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification_campaigns
    ADD CONSTRAINT notification_campaigns_notification_id_fkey FOREIGN KEY (notification_id) REFERENCES public.notifications(id) ON DELETE CASCADE;


--
-- Name: notification_campaigns notification_campaigns_recipient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.notification_campaigns
    ADD CONSTRAINT notification_campaigns_recipient_id_fkey FOREIGN KEY (recipient_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: otp_challenges otp_challenges_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: otp_challenges otp_challenges_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: quotation_items quotation_items_quotation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotation_items
    ADD CONSTRAINT quotation_items_quotation_id_fkey FOREIGN KEY (quotation_id) REFERENCES public.quotations(id) ON DELETE CASCADE;


--
-- Name: quotations quotations_created_by_account_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_created_by_account_id_fkey FOREIGN KEY (created_by_account_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: quotations quotations_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: quotations quotations_enquiry_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_enquiry_id_fkey FOREIGN KEY (enquiry_id) REFERENCES public.enquiries(id) ON DELETE SET NULL;


--
-- Name: quotations quotations_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE SET NULL;


--
-- Name: quotations quotations_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.quotations
    ADD CONSTRAINT quotations_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE SET NULL;


--
-- Name: referrals referrals_referred_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.referrals
    ADD CONSTRAINT referrals_referred_customer_id_fkey FOREIGN KEY (referred_customer_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: referrals referrals_referrer_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.referrals
    ADD CONSTRAINT referrals_referrer_customer_id_fkey FOREIGN KEY (referrer_customer_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- Name: reviews reviews_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: room_allocations room_allocations_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_allocations
    ADD CONSTRAINT room_allocations_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: room_allocations room_allocations_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_allocations
    ADD CONSTRAINT room_allocations_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE SET NULL;


--
-- Name: rooms rooms_hotel_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.rooms
    ADD CONSTRAINT rooms_hotel_id_fkey FOREIGN KEY (hotel_id) REFERENCES public.hotels(id) ON DELETE CASCADE;


--
-- Name: tour_departures tour_departures_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_departures
    ADD CONSTRAINT tour_departures_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE CASCADE;


--
-- Name: tour_details tour_details_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_details
    ADD CONSTRAINT tour_details_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE CASCADE;


--
-- Name: tour_offer_packages tour_offer_packages_offer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_offer_packages
    ADD CONSTRAINT tour_offer_packages_offer_id_fkey FOREIGN KEY (offer_id) REFERENCES public.tour_offers(id) ON DELETE CASCADE;


--
-- Name: tour_offer_packages tour_offer_packages_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_offer_packages
    ADD CONSTRAINT tour_offer_packages_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE CASCADE;


--
-- Name: tour_variants tour_variants_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_variants
    ADD CONSTRAINT tour_variants_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: tour_wishlists tour_wishlists_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_wishlists
    ADD CONSTRAINT tour_wishlists_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE CASCADE;


--
-- Name: tour_wishlists tour_wishlists_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_wishlists
    ADD CONSTRAINT tour_wishlists_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: vehicle_allocations vehicle_allocations_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_allocations
    ADD CONSTRAINT vehicle_allocations_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: vehicle_allocations vehicle_allocations_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_allocations
    ADD CONSTRAINT vehicle_allocations_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id) ON DELETE SET NULL;


--
-- Name: vendor_bookings vendor_bookings_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_bookings
    ADD CONSTRAINT vendor_bookings_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id);


--
-- Name: vendor_bookings vendor_bookings_cost_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_bookings
    ADD CONSTRAINT vendor_bookings_cost_id_fkey FOREIGN KEY (cost_id) REFERENCES public.booking_costs(id);


--
-- Name: vendor_bookings vendor_bookings_vendor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_bookings
    ADD CONSTRAINT vendor_bookings_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES public.vendors(id);


--
-- Name: vendor_expenses vendor_expenses_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_expenses
    ADD CONSTRAINT vendor_expenses_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: vendor_expenses vendor_expenses_cost_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_expenses
    ADD CONSTRAINT vendor_expenses_cost_id_fkey FOREIGN KEY (cost_id) REFERENCES public.booking_costs(id) ON DELETE CASCADE;


--
-- Name: vendor_expenses vendor_expenses_vendor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_expenses
    ADD CONSTRAINT vendor_expenses_vendor_id_fkey FOREIGN KEY (vendor_id) REFERENCES public.vendors(id) ON DELETE CASCADE;


--
-- Name: vendor_payments vendor_payments_booking_cost_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vendor_payments
    ADD CONSTRAINT vendor_payments_booking_cost_id_fkey FOREIGN KEY (booking_cost_id) REFERENCES public.booking_costs(id);


--
-- Name: visitor_events visitor_events_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitor_events
    ADD CONSTRAINT visitor_events_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.visitor_sessions(id) ON DELETE CASCADE;


--
-- Name: visitor_events visitor_events_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitor_events
    ADD CONSTRAINT visitor_events_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE CASCADE;


--
-- Name: visitor_sessions visitor_sessions_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitor_sessions
    ADD CONSTRAINT visitor_sessions_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE CASCADE;


--
-- Name: visitors visitors_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.accounts(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict HjfJyBCe5BJ1X3AlkQ8YTTehzJYWWm3gWo5sCwhLzYNw9YHUn1vixR6GrtHmZOO

