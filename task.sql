--
-- PostgreSQL database dump
--

-- Dumped from database version 12.12 (Ubuntu 12.12-0ubuntu0.20.04.1)
-- Dumped by pg_dump version 12.12 (Ubuntu 12.12-0ubuntu0.20.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
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
-- Name: task; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public.task (
    id integer NOT NULL,
    task character varying(500),
    group_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.task OWNER TO aya_el01;

--
-- Name: task_id_seq; Type: SEQUENCE; Schema: public; Owner: aya_el01
--

CREATE SEQUENCE public.task_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.task_id_seq OWNER TO aya_el01;

--
-- Name: task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aya_el01
--

ALTER SEQUENCE public.task_id_seq OWNED BY public.task.id;


--
-- Name: task id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.task ALTER COLUMN id SET DEFAULT nextval('public.task_id_seq'::regclass);


--
-- Name: task task_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT task_pkey PRIMARY KEY (id);


--
-- Name: task task_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT task_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: task task_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT task_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

