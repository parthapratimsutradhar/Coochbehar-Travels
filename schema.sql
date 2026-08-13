--
-- PostgreSQL database dump
--

\restrict lZl2X9cTWUc1Tpj7wZjKnDxMLF1XY6xMp2iddUUoODWqh23DfS8V9XSoxIM6usW

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
-- Name: custom_tour_requests; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.custom_tour_requests (
    id uuid NOT NULL,
    visitor_id uuid,
    name character varying(100) NOT NULL,
    mobile character varying(20) NOT NULL,
    destination character varying(150) NOT NULL,
    travel_date date,
    adults integer NOT NULL,
    children integer NOT NULL,
    budget numeric(10,2),
    requirements text,
    status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.custom_tour_requests OWNER TO postgres;

--
-- Name: leads; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.leads (
    id uuid NOT NULL,
    visitor_id uuid,
    full_name character varying(100) NOT NULL,
    mobile character varying(20) NOT NULL,
    email character varying(255),
    whatsapp_opt_in boolean NOT NULL,
    lead_score integer NOT NULL,
    status character varying(30) NOT NULL,
    assigned_to character varying(100),
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
    id uuid NOT NULL,
    room_id uuid NOT NULL,
    customer_name character varying(100) NOT NULL,
    mobile character varying(20) NOT NULL,
    check_in date NOT NULL,
    check_out date NOT NULL,
    adults integer NOT NULL,
    children integer NOT NULL,
    total_amount numeric(10,2),
    status character varying(30) NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.room_bookings OWNER TO postgres;

--
-- Name: rooms; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.rooms (
    id uuid NOT NULL,
    room_number character varying(50) NOT NULL,
    room_type character varying(50) NOT NULL,
    capacity integer NOT NULL,
    price_per_night numeric(10,2),
    is_available boolean NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.rooms OWNER TO postgres;

--
-- Name: tour_departures; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_departures (
    id uuid NOT NULL,
    tour_package_id uuid NOT NULL,
    departure_date date NOT NULL,
    status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tour_departures OWNER TO postgres;

--
-- Name: tour_gallery; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_gallery (
    id uuid NOT NULL,
    tour_package_id uuid NOT NULL,
    image_url text NOT NULL,
    sort_order integer NOT NULL
);


ALTER TABLE public.tour_gallery OWNER TO postgres;

--
-- Name: tour_highlights; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_highlights (
    id uuid NOT NULL,
    tour_package_id uuid NOT NULL,
    title character varying(255) NOT NULL,
    sort_order integer NOT NULL
);


ALTER TABLE public.tour_highlights OWNER TO postgres;

--
-- Name: tour_itinerary_days; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_itinerary_days (
    id uuid NOT NULL,
    tour_package_id uuid NOT NULL,
    day_number integer NOT NULL,
    title character varying(255) NOT NULL,
    description text NOT NULL
);


ALTER TABLE public.tour_itinerary_days OWNER TO postgres;

--
-- Name: tour_packages; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_packages (
    id uuid NOT NULL,
    title character varying(255) NOT NULL,
    slug character varying(255) NOT NULL,
    destination character varying(150) NOT NULL,
    duration_days integer NOT NULL,
    duration_nights integer NOT NULL,
    price numeric(10,2) NOT NULL,
    description text,
    featured boolean NOT NULL,
    is_active boolean NOT NULL,
    code character varying(50) NOT NULL,
    season character varying(100),
    image text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.tour_packages OWNER TO postgres;

--
-- Name: tour_route_stops; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tour_route_stops (
    id uuid NOT NULL,
    tour_package_id uuid NOT NULL,
    location character varying(150) NOT NULL,
    nights integer NOT NULL,
    sort_order integer NOT NULL
);


ALTER TABLE public.tour_route_stops OWNER TO postgres;

--
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    role character varying(30) NOT NULL,
    is_active boolean NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.users OWNER TO postgres;

--
-- Name: vehicle_bookings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicle_bookings (
    id uuid NOT NULL,
    vehicle_id uuid NOT NULL,
    customer_name character varying(100) NOT NULL,
    mobile character varying(20) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    adults integer NOT NULL,
    children integer NOT NULL,
    total_amount numeric(10,2),
    status character varying(30) NOT NULL,
    notes text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.vehicle_bookings OWNER TO postgres;

--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehicles (
    id uuid NOT NULL,
    name character varying(100) NOT NULL,
    vehicle_type character varying(50) NOT NULL,
    registration_number character varying(50),
    capacity integer NOT NULL,
    price_per_day numeric(10,2),
    is_available boolean NOT NULL,
    description text,
    created_at timestamp with time zone DEFAULT now() NOT NULL
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
    metadata json,
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.visitor_events OWNER TO postgres;

--
-- Name: visitor_sessions; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visitor_sessions (
    id uuid NOT NULL,
    visitor_id uuid NOT NULL,
    started_at timestamp with time zone DEFAULT now() NOT NULL,
    ended_at timestamp with time zone,
    duration integer NOT NULL,
    landing_page text,
    exit_page text,
    page_views integer NOT NULL,
    referrer text,
    utm_source character varying(100),
    utm_medium character varying(100),
    utm_campaign character varying(100),
    utm_term character varying(100)
);


ALTER TABLE public.visitor_sessions OWNER TO postgres;

--
-- Name: visitors; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.visitors (
    id uuid NOT NULL,
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
    last_seen timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.visitors OWNER TO postgres;

--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: custom_tour_requests custom_tour_requests_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.custom_tour_requests
    ADD CONSTRAINT custom_tour_requests_pkey PRIMARY KEY (id);


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
    ADD CONSTRAINT room_bookings_pkey PRIMARY KEY (id);


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
-- Name: tour_gallery tour_gallery_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_gallery
    ADD CONSTRAINT tour_gallery_pkey PRIMARY KEY (id);


--
-- Name: tour_highlights tour_highlights_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_highlights
    ADD CONSTRAINT tour_highlights_pkey PRIMARY KEY (id);


--
-- Name: tour_itinerary_days tour_itinerary_days_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_itinerary_days
    ADD CONSTRAINT tour_itinerary_days_pkey PRIMARY KEY (id);


--
-- Name: tour_packages tour_packages_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_packages
    ADD CONSTRAINT tour_packages_pkey PRIMARY KEY (id);


--
-- Name: tour_route_stops tour_route_stops_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_route_stops
    ADD CONSTRAINT tour_route_stops_pkey PRIMARY KEY (id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: vehicle_bookings vehicle_bookings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_bookings
    ADD CONSTRAINT vehicle_bookings_pkey PRIMARY KEY (id);


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
-- Name: ix_custom_tour_requests_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_tour_requests_status ON public.custom_tour_requests USING btree (status);


--
-- Name: ix_custom_tour_requests_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_custom_tour_requests_visitor_id ON public.custom_tour_requests USING btree (visitor_id);


--
-- Name: ix_leads_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_email ON public.leads USING btree (email);


--
-- Name: ix_leads_mobile; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_leads_mobile ON public.leads USING btree (mobile);


--
-- Name: ix_leads_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_leads_status ON public.leads USING btree (status);


--
-- Name: ix_leads_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_leads_visitor_id ON public.leads USING btree (visitor_id);


--
-- Name: ix_reviews_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_package_id ON public.reviews USING btree (package_id);


--
-- Name: ix_reviews_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_reviews_visitor_id ON public.reviews USING btree (visitor_id);


--
-- Name: ix_room_bookings_room_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_room_bookings_room_id ON public.room_bookings USING btree (room_id);


--
-- Name: ix_room_bookings_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_room_bookings_status ON public.room_bookings USING btree (status);


--
-- Name: ix_tour_departures_departure_date; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_departures_departure_date ON public.tour_departures USING btree (departure_date);


--
-- Name: ix_tour_departures_tour_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_departures_tour_package_id ON public.tour_departures USING btree (tour_package_id);


--
-- Name: ix_tour_gallery_tour_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_gallery_tour_package_id ON public.tour_gallery USING btree (tour_package_id);


--
-- Name: ix_tour_highlights_tour_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_highlights_tour_package_id ON public.tour_highlights USING btree (tour_package_id);


--
-- Name: ix_tour_itinerary_days_tour_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_itinerary_days_tour_package_id ON public.tour_itinerary_days USING btree (tour_package_id);


--
-- Name: ix_tour_packages_code; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_packages_code ON public.tour_packages USING btree (code);


--
-- Name: ix_tour_packages_slug; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_tour_packages_slug ON public.tour_packages USING btree (slug);


--
-- Name: ix_tour_route_stops_tour_package_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_tour_route_stops_tour_package_id ON public.tour_route_stops USING btree (tour_package_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: ix_vehicle_bookings_status; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_bookings_status ON public.vehicle_bookings USING btree (status);


--
-- Name: ix_vehicle_bookings_vehicle_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_vehicle_bookings_vehicle_id ON public.vehicle_bookings USING btree (vehicle_id);


--
-- Name: ix_visitor_events_created_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_events_created_at ON public.visitor_events USING btree (created_at);


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
-- Name: ix_visitor_sessions_started_at; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_sessions_started_at ON public.visitor_sessions USING btree (started_at);


--
-- Name: ix_visitor_sessions_visitor_id; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX ix_visitor_sessions_visitor_id ON public.visitor_sessions USING btree (visitor_id);


--
-- Name: ix_visitors_fingerprint; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX ix_visitors_fingerprint ON public.visitors USING btree (fingerprint);


--
-- Name: custom_tour_requests custom_tour_requests_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.custom_tour_requests
    ADD CONSTRAINT custom_tour_requests_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


--
-- Name: leads leads_visitor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.leads
    ADD CONSTRAINT leads_visitor_id_fkey FOREIGN KEY (visitor_id) REFERENCES public.visitors(id) ON DELETE SET NULL;


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
-- Name: room_bookings room_bookings_room_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.room_bookings
    ADD CONSTRAINT room_bookings_room_id_fkey FOREIGN KEY (room_id) REFERENCES public.rooms(id) ON DELETE RESTRICT;


--
-- Name: tour_departures tour_departures_tour_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_departures
    ADD CONSTRAINT tour_departures_tour_package_id_fkey FOREIGN KEY (tour_package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: tour_gallery tour_gallery_tour_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_gallery
    ADD CONSTRAINT tour_gallery_tour_package_id_fkey FOREIGN KEY (tour_package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: tour_highlights tour_highlights_tour_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_highlights
    ADD CONSTRAINT tour_highlights_tour_package_id_fkey FOREIGN KEY (tour_package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: tour_itinerary_days tour_itinerary_days_tour_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_itinerary_days
    ADD CONSTRAINT tour_itinerary_days_tour_package_id_fkey FOREIGN KEY (tour_package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: tour_route_stops tour_route_stops_tour_package_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tour_route_stops
    ADD CONSTRAINT tour_route_stops_tour_package_id_fkey FOREIGN KEY (tour_package_id) REFERENCES public.tour_packages(id) ON DELETE CASCADE;


--
-- Name: vehicle_bookings vehicle_bookings_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehicle_bookings
    ADD CONSTRAINT vehicle_bookings_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(id) ON DELETE RESTRICT;


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
-- PostgreSQL database dump complete
--

\unrestrict lZl2X9cTWUc1Tpj7wZjKnDxMLF1XY6xMp2iddUUoODWqh23DfS8V9XSoxIM6usW

