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
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO aya_el01;

--
-- Name: comment; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public.comment (
    id integer NOT NULL,
    user_id integer,
    group_id integer,
    text character varying(500),
    date timestamp without time zone
);


ALTER TABLE public.comment OWNER TO aya_el01;

--
-- Name: comment_id_seq; Type: SEQUENCE; Schema: public; Owner: aya_el01
--

CREATE SEQUENCE public.comment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.comment_id_seq OWNER TO aya_el01;

--
-- Name: comment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aya_el01
--

ALTER SEQUENCE public.comment_id_seq OWNED BY public.comment.id;


--
-- Name: expense; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public.expense (
    id integer NOT NULL,
    description character varying(200),
    amount double precision,
    user_id integer,
    group_id integer,
    approved boolean,
    last_updated timestamp without time zone
);


ALTER TABLE public.expense OWNER TO aya_el01;

--
-- Name: expense_id_seq; Type: SEQUENCE; Schema: public; Owner: aya_el01
--

CREATE SEQUENCE public.expense_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.expense_id_seq OWNER TO aya_el01;

--
-- Name: expense_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aya_el01
--

ALTER SEQUENCE public.expense_id_seq OWNED BY public.expense.id;


--
-- Name: group; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public."group" (
    id integer NOT NULL,
    name character varying(100)
);


ALTER TABLE public."group" OWNER TO aya_el01;

--
-- Name: group_id_seq; Type: SEQUENCE; Schema: public; Owner: aya_el01
--

CREATE SEQUENCE public.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.group_id_seq OWNER TO aya_el01;

--
-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aya_el01
--

ALTER SEQUENCE public.group_id_seq OWNED BY public."group".id;


--
-- Name: group_member; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public.group_member (
    id integer NOT NULL,
    weight integer DEFAULT 1,
    last_updated timestamp without time zone,
    user_id integer,
    group_id integer
);


ALTER TABLE public.group_member OWNER TO aya_el01;

--
-- Name: group_member_id_seq; Type: SEQUENCE; Schema: public; Owner: aya_el01
--

CREATE SEQUENCE public.group_member_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.group_member_id_seq OWNER TO aya_el01;

--
-- Name: group_member_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aya_el01
--

ALTER SEQUENCE public.group_member_id_seq OWNED BY public.group_member.id;


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
-- Name: user; Type: TABLE; Schema: public; Owner: aya_el01
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(64),
    password character varying(128),
    email character varying(120),
    is_logged_in boolean
);


ALTER TABLE public."user" OWNER TO aya_el01;

--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: aya_el01
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_id_seq OWNER TO aya_el01;

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: aya_el01
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: comment id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.comment ALTER COLUMN id SET DEFAULT nextval('public.comment_id_seq'::regclass);


--
-- Name: expense id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.expense ALTER COLUMN id SET DEFAULT nextval('public.expense_id_seq'::regclass);


--
-- Name: group id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public."group" ALTER COLUMN id SET DEFAULT nextval('public.group_id_seq'::regclass);


--
-- Name: group_member id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.group_member ALTER COLUMN id SET DEFAULT nextval('public.group_member_id_seq'::regclass);


--
-- Name: task id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.task ALTER COLUMN id SET DEFAULT nextval('public.task_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: comment comment_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_pkey PRIMARY KEY (id);


--
-- Name: expense expense_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.expense
    ADD CONSTRAINT expense_pkey PRIMARY KEY (id);


--
-- Name: group_member group_member_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.group_member
    ADD CONSTRAINT group_member_pkey PRIMARY KEY (id);


--
-- Name: group group_name_key; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public."group"
    ADD CONSTRAINT group_name_key UNIQUE (name);


--
-- Name: group group_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public."group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);


--
-- Name: task task_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT task_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: ix_user_email; Type: INDEX; Schema: public; Owner: aya_el01
--

CREATE UNIQUE INDEX ix_user_email ON public."user" USING btree (email);


--
-- Name: ix_user_username; Type: INDEX; Schema: public; Owner: aya_el01
--

CREATE UNIQUE INDEX ix_user_username ON public."user" USING btree (username);


--
-- Name: comment comment_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: comment comment_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: expense expense_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.expense
    ADD CONSTRAINT expense_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: expense expense_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.expense
    ADD CONSTRAINT expense_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: group_member group_member_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.group_member
    ADD CONSTRAINT group_member_group_id_fkey FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: group_member group_member_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: aya_el01
--

ALTER TABLE ONLY public.group_member
    ADD CONSTRAINT group_member_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


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

