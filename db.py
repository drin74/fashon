import mysql.connector
from mysql.connector import Error
from config import DB_CONFIG


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def execute(query, params=None, fetch=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(query, params or ())
        if fetch:
            return cursor.fetchall()
        conn.commit()
        return cursor.lastrowid
    except Error as e:
        print("DB error:", e)
        return [] if fetch else None
    finally:
        cursor.close()
        conn.close()


# ==================== MODELS ====================
def get_models(search="", order_by="name", order_dir="ASC", only_fav=False):
    allowed_sort = {"name", "category", "season", "price", "created_at"}
    if order_by not in allowed_sort:
        order_by = "name"
    order_dir = "DESC" if order_dir.upper() == "DESC" else "ASC"

    q = ("SELECT m.*, c.name AS collection_name FROM models m "
         "LEFT JOIN collections c ON m.collection_id = c.id WHERE 1=1")
    params = []
    if search:
        q += " AND (m.name LIKE %s OR m.category LIKE %s OR m.fabric LIKE %s)"
        like = f"%{search}%"
        params += [like, like, like]
    if only_fav:
        q += " AND m.is_favorite = 1"
    q += f" ORDER BY m.{order_by} {order_dir}"
    return execute(q, params, fetch=True)


def get_model(mid):
    res = execute("SELECT * FROM models WHERE id=%s", (mid,), fetch=True)
    return res[0] if res else None


def add_model(data):
    return execute(
        """INSERT INTO models
        (name, category, season, color_hex, fabric, price, description, image_path, collection_id, is_favorite)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (data["name"], data["category"], data["season"], data["color_hex"],
         data["fabric"], data["price"], data["description"], data["image_path"],
         data["collection_id"], data["is_favorite"])
    )


def update_model(mid, data):
    execute(
        """UPDATE models SET name=%s, category=%s, season=%s, color_hex=%s,
        fabric=%s, price=%s, description=%s, image_path=%s,
        collection_id=%s, is_favorite=%s WHERE id=%s""",
        (data["name"], data["category"], data["season"], data["color_hex"],
         data["fabric"], data["price"], data["description"], data["image_path"],
         data["collection_id"], data["is_favorite"], mid)
    )


def delete_model(mid):
    execute("DELETE FROM models WHERE id=%s", (mid,))


def toggle_favorite(mid):
    execute("UPDATE models SET is_favorite = NOT is_favorite WHERE id=%s", (mid,))


# ==================== COLLECTIONS ====================
def get_collections():
    return execute("SELECT * FROM collections ORDER BY name", fetch=True)


def add_collection(name, description):
    return execute("INSERT INTO collections (name, description) VALUES (%s,%s)",
                   (name, description))


def delete_collection(cid):
    execute("DELETE FROM collections WHERE id=%s", (cid,))


# ==================== DESIGNS ====================
def add_design(name, template, color, canvas_json, preview_path, model_id=None):
    return execute(
        """INSERT INTO designs (name, template, product_color, canvas_json, preview_path, model_id)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (name, template, color, canvas_json, preview_path, model_id))


def get_designs():
    return execute("SELECT * FROM designs ORDER BY created_at DESC", fetch=True)


def get_design(did):
    res = execute("SELECT * FROM designs WHERE id=%s", (did,), fetch=True)
    return res[0] if res else None


def update_design(did, name, color, canvas_json, preview_path):
    execute(
        """UPDATE designs SET name=%s, product_color=%s,
           canvas_json=%s, preview_path=%s WHERE id=%s""",
        (name, color, canvas_json, preview_path, did))


def delete_design(did):
    execute("DELETE FROM designs WHERE id=%s", (did,))