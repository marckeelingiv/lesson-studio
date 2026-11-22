# Presentation stays here; subject setup/lifecycle belongs to DE for Fun.
default:
    @just --list

# Set DE_FOR_FUN_DIR to the explicit companion checkout; see lesson_studio/README.md.
lesson:
    @just --justfile "${DE_FOR_FUN_DIR:?Set DE_FOR_FUN_DIR to the DE for Fun companion checkout}/justfile" lesson

lesson-stop:
    @just --justfile "${DE_FOR_FUN_DIR:?Set DE_FOR_FUN_DIR to the DE for Fun companion checkout}/justfile" lesson-stop

lesson-rebuild:
    @just --justfile "${DE_FOR_FUN_DIR:?Set DE_FOR_FUN_DIR to the DE for Fun companion checkout}/justfile" lesson-rebuild
