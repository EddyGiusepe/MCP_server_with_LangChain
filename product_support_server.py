#!/usr/bin/env python
"""
Senior Data Scientist/AI Engineering.: Dr. Eddy Giusepe Chirinos Isidro

Script product_support_server.py
================================
Em este script vamos criar nosso SERVER MCP, ademais vamos criar duas tabelas
chamdas faq e orders.
"""

import sqlite3
import os
import struct
from pathlib import Path
from dotenv import load_dotenv
import sqlite_vec
from fastmcp import FastMCP
from langchain_openai import OpenAIEmbeddings

load_dotenv()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "product_support.db")

mcp = FastMCP("Product Support Server")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faq (
            keyword TEXT PRIMARY KEY,
            answer TEXT NOT NULL,
            embedding BLOB
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            status TEXT NOT NULL
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM faq")
    if cursor.fetchone()[0] == 0:
        faq_data = [
            ("envio", "O envio padrão geralmente leva de 3 a 5 dias úteis."),
            ("reembolso", "Você pode solicitar um reembolso total em até 30 dias após a entrega."),
            ("password", "Você pode redefinir sua senha em Settings > Account > Reset Password."),
        ]
        cursor.executemany("INSERT INTO faq (keyword, answer) VALUES (?, ?)", faq_data)
    cursor.execute("SELECT COUNT(*) FROM orders")
    if cursor.fetchone()[0] == 0:
        orders_data = [
            ("ORD1001", "Seu pedido foi enviado."),
            ("ORD1002", "Seu pedido está sendo processado."),
            ("ORD1003", "Seu pedido foi entregue."),
        ]
        cursor.executemany("INSERT INTO orders (order_id, status) VALUES (?, ?)", orders_data)
    conn.commit()
    conn.close()


def generate_embeddings_for_existing_faqs():
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keyword, answer, embedding FROM faq WHERE embedding IS NULL")
    rows = cursor.fetchall()
    if not rows:
        conn.close()
        return
    answers = [row["answer"] for row in rows]
    vectors = embeddings_model.embed_documents(answers)
    for row, vector in zip(rows, vectors):
        vector_bytes = struct.pack(f"{len(vector)}f", *vector)
        cursor.execute(
            "UPDATE faq SET embedding = ? WHERE keyword = ?",
            (sqlite3.Binary(vector_bytes), row["keyword"]),
        )
    conn.commit()
    conn.close()


init_db()
generate_embeddings_for_existing_faqs()


@mcp.tool
def search_product_faq(query: str) -> str:
    """Search product support FAQs for questions about shipping, refunds, or passwords."""
    embeddings_model = OpenAIEmbeddings(model="text-embedding-3-small")
    query_vector = embeddings_model.embed_query(query)
    query_vector_bytes = struct.pack(f"{len(query_vector)}f", *query_vector)
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT keyword, answer,
               vec_distance_cosine(embedding, ?) as score
        FROM faq
        ORDER BY score
        LIMIT 1
    """, (sqlite3.Binary(query_vector_bytes),))
    row = cursor.fetchone()
    conn.close()
    COSINE_THRESHOLD = 0.70
    if row and row["score"] < COSINE_THRESHOLD:
        return row["answer"]
    return "Desculpe, não encontrei informações relevantes para essa pergunta."


@mcp.tool
def check_order_status(order_id: str) -> str:
    """Check the current status of an order using its order ID, for example ORD1001."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM orders WHERE order_id = ?", (order_id.strip().upper(),))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["status"]
    return "Pedido não encontrado."


if __name__ == "__main__":
    mcp.run()
