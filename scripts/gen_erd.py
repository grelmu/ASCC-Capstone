import os
import subprocess


def main():

    diagram_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "dist", "diagrams"
    )
    os.makedirs(diagram_dir, exist_ok=True)

    subprocess.check_call(
        [
            "erdantic",
            "mppw.models.Project",
            "mppw.models.Operation",
            "mppw.models.MaterialArtifact",
            "mppw.models.DigitalArtifact",
            "-o",
            os.path.join(diagram_dir, "projects_erd.png"),
        ]
    )

    subprocess.check_call(
        [
            "erdantic",
            "mppw.models.StoredSchema",
            "mppw.schemas.OperationSchema",
            "mppw.schemas.ArtifactSchema",
            "-o",
            os.path.join(diagram_dir, "schemas_erd.png"),
        ]
    )


if __name__ == "__main__":
    main()
