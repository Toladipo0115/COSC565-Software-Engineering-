EngageTrace UML Submission
COSC565 Software Engineering
Tolulope Oladipo
Blackboard
Upload "COSC565-EngageTraceUML Diagrams-Toladipo.pdf". It contains all three UML models and their supporting text. The diagrams retain vector graphics.
GitHub
Upload the uml-diagrams folder to the repository root. Each diagram type has its own subfolder: "use-case diagram", "sequence diagram", and "class diagram". SVG files are vector; PNG images are high-resolution. The class model has two linked image views for readability: Application and Domain.
The package also includes the written explanations and editable source where available:
use-case diagram: EngageTrace_Use_Case (PNG, SVG, PDF) and Use_Case_Descriptions.md
sequence diagram: EngageTrace_Sequence (PNG, SVG, PDF, PUML source) and Sequence_Explanation.md
class diagram: EngageTrace_Class_Application and EngageTrace_Class_Domain (PNG, SVG), EngageTrace_Class_Diagram.pdf and .puml source, and Class_Diagram_Guide.md


## Application implementation

US-01 adds a local Python CSV ingestion command and SQLite staging. See [setup, usage and acceptance evidence](docs/US-01.md).

```sh
python -m engagetrace import --input-dir examples/oulad-synthetic --database data/demo.sqlite3
python -m unittest discover -s tests -v
```
