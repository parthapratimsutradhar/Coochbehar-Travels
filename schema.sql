--
-- PostgreSQL database dump
--

\restrict ZnT5dWq8H9xis4huCIjZvPJ13doTLgbuWQdm0rFopLUmw1POSfSrmzKJENQ1L1z

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
-- Name: booking_status; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.booking_status AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED',
    'COMPLETED'
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
-- Name: user_role; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE public.user_role AS ENUM (
    'ADMIN',
    'STAFF'
);


ALTER TYPE public.user_role OWNER TO postgres;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: auth_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.auth_sessions (
    id uuid NOT NULL,
    user_id uuid,
    customer_id uuid,
    actor_type character varying(20) DEFAULT 'USER'::character varying NOT NULL,
    refresh_token_hash character varying(255) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_used_at timestamp with time zone DEFAULT now() NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    user_agent character varying(500),
    ip_address character varying(45)
);


ALTER TABLE public.auth_sessions OWNER TO postgres;

--
-- Name: customers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.customers (
    id uuid NOT NULL,
    customer_code character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    mobile character varying(20),
    email character varying(255),
    address character varying(255),
    emergency_contact_name character varying(100),
    emergency_contact_mobile character varying(20),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    source public.lead_source NOT NULL,
    is_imported boolean NOT NULL,
    profile_pic character varying(500)
);


ALTER TABLE public.customers OWNER TO postgres;

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
    travel_duration character varying(50),
    pax_no integer,
    no_room integer,
    vehicle_type character varying(50),
    meal_plan character varying(50),
    special_requirements text,
    enquirer_name character varying(50),
    enquirer_phone character varying(20)
);


ALTER TABLE public.enquiries OWNER TO postgres;

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
-- Name: lead_activities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.lead_activities (
    id uuid NOT NULL,
    lead_id uuid NOT NULL,
    user_id uuid,
    channel public.enquiry_channel NOT NULL,
    activity_type character varying(50) NOT NULL,
    notes text,
    next_follow_up_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.lead_activities OWNER TO postgres;

--
-- Name: lead_activities lead_activities_lead_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT lead_activities_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.leads(id) ON DELETE CASCADE;

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
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id uuid NOT NULL,
    review_code character varying(20) NOT NULL,
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
    CONSTRAINT ck_reviews_rating CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO postgres;

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
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.rooms OWNER TO postgres;

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
    departures_dates jsonb NOT NULL,
    itinerary jsonb NOT NULL,
    route_stops jsonb NOT NULL,
    id uuid NOT NULL
);


ALTER TABLE public.tour_details OWNER TO postgres;

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
    seats integer,
    is_default boolean NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    badge character varying(50),
    availability character varying(20) DEFAULT 'AVAILABLE'::character varying,
    slug character varying(30) NOT NULL
);


ALTER TABLE public.tour_variants OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    user_code character varying(20) NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    mobile character varying(20) NOT NULL,
    role public.user_role NOT NULL,
    is_active boolean NOT NULL,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    profile_pic character varying(500)
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicles (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    registration_number character varying(50) NOT NULL,
    capacity integer NOT NULL,
    price_per_day numeric(10,2) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vehicles OWNER TO postgres;

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
    lead_score integer NOT NULL,
    first_seen timestamp with time zone DEFAULT now() NOT NULL,
    last_seen timestamp with time zone DEFAULT now() NOT NULL,
    customer_id uuid
);


ALTER TABLE public.visitors OWNER TO postgres;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: auth_sessions auth_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: enquiries enquiries_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_pkey PRIMARY KEY (id);


--
-- Name: google_oauth_states google_oauth_states_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_oauth_states
    ADD CONSTRAINT google_oauth_states_pkey PRIMARY KEY (id);


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
-- Name: otp_challenges otp_challenges_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


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
-- Name: tour_details tour_details_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_details
    ADD CONSTRAINT tour_details_pkey PRIMARY KEY (variant_id);


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
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


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
-- Name: ix_auth_sessions_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_auth_sessions_customer_id ON public.auth_sessions USING btree (customer_id);


--
-- Name: ix_auth_sessions_refresh_token_hash; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_auth_sessions_refresh_token_hash ON public.auth_sessions USING btree (refresh_token_hash);


--
-- Name: ix_auth_sessions_user_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_auth_sessions_user_id ON public.auth_sessions USING btree (user_id);


--
-- Name: ix_customers_customer_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_customers_customer_code ON public.customers USING btree (customer_code);


--
-- Name: ix_customers_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_customers_email ON public.customers USING btree (email);


--
-- Name: ix_customers_mobile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_customers_mobile ON public.customers USING btree (mobile);


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
-- Name: ix_google_oauth_states_state_token; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_google_oauth_states_state_token ON public.google_oauth_states USING btree (state_token);


--
-- Name: ix_google_oauth_states_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_google_oauth_states_visitor_id ON public.google_oauth_states USING btree (visitor_id);


--
-- Name: ix_lead_activities_next_follow_up_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lead_activities_next_follow_up_at ON public.lead_activities USING btree (next_follow_up_at);

--
-- Name: ix_lead_activities_lead_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_lead_activities_lead_id ON public.lead_activities USING btree (lead_id);


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
-- Name: ix_reviews_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_customer_id ON public.reviews USING btree (customer_id);


--
-- Name: ix_reviews_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_package_id ON public.reviews USING btree (package_id);


--
-- Name: ix_reviews_review_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_reviews_review_code ON public.reviews USING btree (review_code);


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
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_users_mobile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_mobile ON public.users USING btree (mobile);


--
-- Name: ix_users_user_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_user_code ON public.users USING btree (user_code);


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
-- Name: auth_sessions auth_sessions_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE CASCADE;


--
-- Name: auth_sessions auth_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: enquiries enquiries_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.enquiries
    ADD CONSTRAINT enquiries_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE SET NULL;


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
-- Name: google_oauth_states google_oauth_states_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.google_oauth_states
    ADD CONSTRAINT google_oauth_states_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: lead_activities lead_activities_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.lead_activities
    ADD CONSTRAINT lead_activities_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: leads leads_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE SET NULL;


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
-- Name: otp_challenges otp_challenges_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE SET NULL;


--
-- Name: otp_challenges otp_challenges_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.otp_challenges
    ADD CONSTRAINT otp_challenges_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: reviews reviews_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE SET NULL;


--
-- Name: reviews reviews_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: tour_details tour_details_variant_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_details
    ADD CONSTRAINT tour_details_variant_id_fkey FOREIGN KEY (variant_id) REFERENCES public.tour_variants(id) ON DELETE CASCADE;


--
-- Name: tour_variants tour_variants_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_variants
    ADD CONSTRAINT tour_variants_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


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
    ADD CONSTRAINT visitors_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict ZnT5dWq8H9xis4huCIjZvPJ13doTLgbuWQdm0rFopLUmw1POSfSrmzKJENQ1L1z

