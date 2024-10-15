"""
Das Skript manipuliert die SCUM-Datenbank im Einzelspielermodus
Man kann das Niveau der Fertigkeiten und Attribute bis auf das Maximum erhöhen oder den Wert, bis erreichen des max. Wert, selbst festlegen.
"""

from dataclasses import dataclass
import datetime as dt
import os
from pathlib import Path
import shutil
import sqlite3
import struct
import traceback
from typing import Literal

## Konfiguration ##

# Hauptattribute #
SET_ATTRIBUTES = {
    "BaseStrength": 7.0,  # 1.0 bis 8.0
    "BaseConstitution": 5.0,  # 1.0 bis 5.0
    "BaseDexterity": 5.0,  # 1.0 bis 5.0
    "BaseIntelligence": 5.0,  # 1.0 bis 5.0
}

# Fähigkeiten #
"""
Man kann Fähigkeiten aus der Liste unten entfernen und sie werden nicht geändert.
Wenn dem Spiel eine neue Fertigkeit hinzugefügt wird, kann diese hinzugefügt werden.

Die erste Zahl in jeder Zeile ist die Fähigkeitsstufe (0 - 3).

Die zweite Zahl ist die Fertigkeitserfahrung (0 - 10000000)
"""

SET_SKILLS = {
    "BoxingSkill": (3, 10000000),
    "AwarenessSkill": (3, 10000000),
    "RiflesSkill": (3, 10000000),
    "SnipingSkill": (3, 10000000),
    "CamouflageSkill": (3, 10000000),
    "SurvivalSkill": (3, 10000000),
    "MeleeWeaponsSkill": (3, 10000000),
    "HandgunSkill": (3, 10000000),
    "RunningSkill": (3, 10000000),
    "EnduranceSkill": (3, 10000000),
    "TacticsSkill": (3, 10000000),
    "CookingSkill": (3, 10000000),
    "ThieverySkill": (3, 10000000),
    "ArcherySkill": (3, 10000000),
    "DrivingSkill": (3, 10000000),
    "EngineeringSkill": (3, 10000000),
    "DemolitionSkill": (3, 10000000),
    "MedicalSkill": (3, 10000000),
    "MotorcycleSkill": (3, 10000000),
    "StealthSkill": (3, 10000000),
    "AviationSkill": (3, 10000000),
    "ResistanceSkill": (3, 10000000),
    "FarmingSkill": (3, 10000000),
}

# Konstanten werden abgefragt
# Spiel im Standardpfad installiert

USER = os.getlogin()
DB_PATH = Path(f"C:/Users/{USER}/AppData/Local/SCUM/Saved/SaveFiles/SCUM.db")

BODY_SIM_KEY_PADDING = 5
BODY_SIM_VALUE_PADDING = 10


@dataclass
class PropertyType:
    """Klasse zum Definieren von Eigenschaftstypen"""

    name: bytes
    width: int
    # Wird zum Konvertieren mit Python verwendet
    struct_type: Literal["<d", "<f", "<?"]


DoubleProperty = PropertyType(name=b"DoubleProperty", width=8, struct_type="<d")
FloatProperty = PropertyType(name=b"FloatProperty", width=4, struct_type="<f")
BoolProperty = PropertyType(name=b"BoolProperty", width=1, struct_type="<?")


def load_prisoner(con: sqlite3.Connection, id: int):
    """Charakter wird aus der Datenbank geladen."""
    cur = con.execute("SELECT * FROM prisoner WHERE id = ?", (id,))
    result = {desc[0]: val for desc, val in zip(cur.description, cur.fetchone())}
    return result


def save_prisoner(con: sqlite3.Connection, prisoner: dict):
    """Aktualisiert den Charakter in der Datenbank."""
    return con.execute(
        "UPDATE prisoner SET body_simulation = ? WHERE id = ?",
        (prisoner["body_simulation"], prisoner["id"]),
    )

def update_body_sim(body_sim: bytearray, key: bytes, value: float, property_type: PropertyType):
    
    key_offset = body_sim.index(key)
    
    assert (
        body_sim[
            key_offset
            + len(key)
            + BODY_SIM_KEY_PADDING : key_offset
            + len(key)
            + BODY_SIM_KEY_PADDING
            + len(property_type.name)
        ]
        == property_type.name
    )

    value_offset = (
        key_offset
        + len(key)
        + BODY_SIM_KEY_PADDING
        + len(property_type.name)
        + BODY_SIM_VALUE_PADDING
    )

    value_bytes = struct.pack(property_type.struct_type, value)

    body_sim[value_offset : value_offset + property_type.width] = value_bytes


def update_skills(con: sqlite3.Connection, prisoner: dict):
    """Setzt alle Fertigkeiten in der Datenbank auf die maximale Stufe."""

    for (name,) in con.execute(
        "SELECT name FROM prisoner_skill WHERE prisoner_id = ?", (prisoner["id"],)
    ):
        if name not in SET_SKILLS:
            continue

        new_level, new_experience = SET_SKILLS[name]

        con.execute(
            "UPDATE prisoner_skill SET level = ?, experience = ? WHERE prisoner_id = ? AND name = ?",
            (new_level, new_experience, prisoner["id"], name),
        )


def choose_prisoner(con: sqlite3.Connection):
    """Wählen Sie den zu aktualisierenden Gefangenen aus."""
    cur = con.execute(
        "SELECT prisoner.id, user_profile.name FROM prisoner LEFT JOIN user_profile ON prisoner.user_profile_id = user_profile.id WHERE user_profile.authority_name is ?",
        (None,),
    )
    print("\nGefangener im lokalen Einzelspielermodus gefunden:\n")
    for id, name in cur:
        print(f'"{name}" mit ID {id}')
    return int(input("\nGeben Sie die ID des Gefangenen ein: "))


def main():
    print("Datenbank wird gesichert... ")
    filename_safe_iso = dt.datetime.now().isoformat().replace(":", "-")
    backup_path = DB_PATH.with_name(f"SCUM-bak-{filename_safe_iso}.db")
    shutil.copy(DB_PATH, backup_path)
    print(f"Gesichert auf: {backup_path}")

    print("\nVerbindung zur Datenbank wird hergestellt...")
    con = sqlite3.connect(DB_PATH)

    # Wähle einen Gefangenen aus
    prisoner_id = choose_prisoner(con)

    print(f"Lade den Gefangenen mit ID {prisoner_id}...")
    prisoner = load_prisoner(con, prisoner_id)

    print("\nAttribute aktualisieren... ", end="")
    body_sim = bytearray(prisoner["body_simulation"])

    for attribute, value in SET_ATTRIBUTES.items():
        update_body_sim(
            body_sim,
            attribute.encode("ascii"),
            value,
            DoubleProperty,
        )

    prisoner["body_simulation"] = bytes(body_sim)

    save_prisoner(con, prisoner)
    print("Erfolgt!")

    print("Fähigkeiten aktualisieren... ", end="")
    update_skills(con, prisoner)
    print("Erfolgt!")

    con.commit()
    input("\nDrücken Sie die Eingabetaste, um den Vorgang zu beenden.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBeenden...")
    except Exception:
        print("\n\nEin Fehler ist aufgetreten...\n\n")
        traceback.print_exc()
        input("\n\nDrücken Sie die Eingabetaste, um den Vorgang zu beenden.")
