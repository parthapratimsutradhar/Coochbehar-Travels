--
-- PostgreSQL database dump
--

\restrict 4yRbprUsjvL7rnhCD2hx6qSS4drYR0M8F5Wulm0Du4uUPVXWZGSskd0djxKXdOQ

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
-- Name: bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bookings (
    id uuid NOT NULL,
    booking_code character varying(20) NOT NULL,
    customer_id uuid NOT NULL,
    booking_type public.booking_type NOT NULL,
    status public.booking_status NOT NULL,
    total_amount numeric(12,2) NOT NULL,
    remarks character varying(500),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.bookings OWNER TO postgres;

--
-- Name: custom_tour_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.custom_tour_requests (
    id uuid NOT NULL,
    request_code character varying(20) NOT NULL,
    visitor_id uuid,
    name character varying(100) NOT NULL,
    mobile character varying(20) NOT NULL,
    destination character varying(150) NOT NULL,
    travel_date date,
    travel_duration character varying(50),
    pax_no integer NOT NULL,
    no_room integer NOT NULL,
    vehicle_type character varying(50),
    meal_plan character varying(50),
    special_requirements text,
    status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.custom_tour_requests OWNER TO postgres;

--
-- Name: customers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.customers (
    id uuid NOT NULL,
    customer_code character varying(20) NOT NULL,
    lead_id uuid,
    name character varying(100) NOT NULL,
    mobile character varying(20),
    email character varying(255),
    address character varying(255),
    emergency_contact_name character varying(100),
    emergency_contact_mobile character varying(20),
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.customers OWNER TO postgres;

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
    status character varying(30) NOT NULL,
    notes text,
    last_contacted_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.leads OWNER TO postgres;

--
-- Name: reviews; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reviews (
    id uuid NOT NULL,
    review_code character varying(20) NOT NULL,
    package_id uuid NOT NULL,
    visitor_id uuid,
    name character varying(100) NOT NULL,
    rating integer NOT NULL,
    review text NOT NULL,
    is_verified boolean NOT NULL,
    is_published boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_reviews_rating CHECK (((rating >= 1) AND (rating <= 5)))
);


ALTER TABLE public.reviews OWNER TO postgres;

--
-- Name: room_bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.room_bookings (
    booking_id uuid NOT NULL,
    room_booking_code character varying(20) NOT NULL,
    room_id uuid NOT NULL,
    check_in date NOT NULL,
    check_out date NOT NULL,
    adults integer NOT NULL,
    children integer NOT NULL
);


ALTER TABLE public.room_bookings OWNER TO postgres;

--
-- Name: rooms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rooms (
    id uuid NOT NULL,
    room_code character varying(20),
    room_number character varying(20),
    room_type character varying(50),
    capacity integer,
    price_per_night numeric(10,2),
    description text,
    is_active boolean,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.rooms OWNER TO postgres;

--
-- Name: tour_details; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_details (
    variant_id uuid NOT NULL,
    tour_detail_code character varying(20) NOT NULL,
    banner jsonb NOT NULL,
    gallery jsonb NOT NULL,
    highlights jsonb NOT NULL,
    inclusions jsonb NOT NULL,
    exclusions jsonb NOT NULL,
    departures_dates jsonb NOT NULL,
    itinerary jsonb NOT NULL,
    route_stops jsonb NOT NULL
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
    variant_code character varying(30) NOT NULL,
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
    updated_at timestamp with time zone DEFAULT now() NOT NULL
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
    password_hash character varying(255) NOT NULL,
    role public.user_role NOT NULL,
    is_active boolean NOT NULL,
    last_login timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: vehicle_bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_bookings (
    booking_id uuid NOT NULL,
    vehicle_id uuid NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    adults integer NOT NULL,
    children integer NOT NULL
);


ALTER TABLE public.vehicle_bookings OWNER TO postgres;

--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicles (
    id uuid NOT NULL,
    vehicle_code character varying(20) NOT NULL,
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
    event_code character varying(20) NOT NULL,
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
    session_code character varying(20) NOT NULL,
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
    lead_id uuid,
    first_seen timestamp with time zone DEFAULT now() NOT NULL,
    last_seen timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.visitors OWNER TO postgres;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: bookings bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_pkey PRIMARY KEY (id);


--
-- Name: custom_tour_requests custom_tour_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.custom_tour_requests
    ADD CONSTRAINT custom_tour_requests_pkey PRIMARY KEY (id);


--
-- Name: customers customers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_pkey PRIMARY KEY (id);


--
-- Name: leads leads_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_pkey PRIMARY KEY (id);


--
-- Name: reviews reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_pkey PRIMARY KEY (id);


--
-- Name: room_bookings room_bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_bookings
    ADD CONSTRAINT room_bookings_pkey PRIMARY KEY (booking_id);


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
-- Name: vehicle_bookings vehicle_bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_bookings
    ADD CONSTRAINT vehicle_bookings_pkey PRIMARY KEY (booking_id);


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
-- Name: ix_bookings_booking_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_bookings_booking_code ON public.bookings USING btree (booking_code);


--
-- Name: ix_bookings_customer_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_bookings_customer_id ON public.bookings USING btree (customer_id);


--
-- Name: ix_custom_tour_requests_request_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_custom_tour_requests_request_code ON public.custom_tour_requests USING btree (request_code);


--
-- Name: ix_customers_customer_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_customers_customer_code ON public.customers USING btree (customer_code);


--
-- Name: ix_customers_lead_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_customers_lead_id ON public.customers USING btree (lead_id);


--
-- Name: ix_leads_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_email ON public.leads USING btree (email);


--
-- Name: ix_leads_lead_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_leads_lead_code ON public.leads USING btree (lead_code);


--
-- Name: ix_leads_mobile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_leads_mobile ON public.leads USING btree (mobile);


--
-- Name: ix_leads_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_status ON public.leads USING btree (status);


--
-- Name: ix_reviews_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_package_id ON public.reviews USING btree (package_id);


--
-- Name: ix_reviews_review_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_reviews_review_code ON public.reviews USING btree (review_code);


--
-- Name: ix_reviews_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_visitor_id ON public.reviews USING btree (visitor_id);


--
-- Name: ix_room_bookings_room_booking_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_room_bookings_room_booking_code ON public.room_bookings USING btree (room_booking_code);


--
-- Name: ix_rooms_room_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_rooms_room_code ON public.rooms USING btree (room_code);


--
-- Name: ix_tour_details_tour_detail_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_details_tour_detail_code ON public.tour_details USING btree (tour_detail_code);


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
-- Name: ix_tour_variants_variant_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_variants_variant_code ON public.tour_variants USING btree (variant_code);


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
-- Name: ix_vehicles_vehicle_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_vehicles_vehicle_code ON public.vehicles USING btree (vehicle_code);


--
-- Name: ix_visitor_events_event_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitor_events_event_code ON public.visitor_events USING btree (event_code);


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
-- Name: ix_visitor_sessions_session_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitor_sessions_session_code ON public.visitor_sessions USING btree (session_code);


--
-- Name: ix_visitor_sessions_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_sessions_visitor_id ON public.visitor_sessions USING btree (visitor_id);


--
-- Name: ix_visitors_fingerprint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitors_fingerprint ON public.visitors USING btree (fingerprint);


--
-- Name: ix_visitors_lead_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitors_lead_id ON public.visitors USING btree (lead_id);


--
-- Name: ix_visitors_visitor_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitors_visitor_code ON public.visitors USING btree (visitor_code);


--
-- Name: bookings bookings_customer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bookings
    ADD CONSTRAINT bookings_customer_id_fkey FOREIGN KEY (customer_id) REFERENCES public.customers(id);


--
-- Name: custom_tour_requests custom_tour_requests_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.custom_tour_requests
    ADD CONSTRAINT custom_tour_requests_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: customers customers_lead_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.customers
    ADD CONSTRAINT customers_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.leads(id) ON DELETE RESTRICT;


--
-- Name: reviews reviews_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_package_id_fkey FOREIGN KEY (package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: reviews reviews_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT reviews_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: room_bookings room_bookings_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_bookings
    ADD CONSTRAINT room_bookings_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: room_bookings room_bookings_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_bookings
    ADD CONSTRAINT room_bookings_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id);


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
-- Name: vehicle_bookings vehicle_bookings_booking_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_bookings
    ADD CONSTRAINT vehicle_bookings_booking_id_fkey FOREIGN KEY (booking_id) REFERENCES public.bookings(id) ON DELETE CASCADE;


--
-- Name: vehicle_bookings vehicle_bookings_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_bookings
    ADD CONSTRAINT vehicle_bookings_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id);


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
-- Name: visitors visitors_lead_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.visitors
    ADD CONSTRAINT visitors_lead_id_fkey FOREIGN KEY (lead_id) REFERENCES public.leads(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--

\unrestrict 4yRbprUsjvL7rnhCD2hx6qSS4drYR0M8F5Wulm0Du4uUPVXWZGSskd0djxKXdOQ

