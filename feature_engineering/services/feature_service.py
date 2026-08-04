# ============================================================
# Feature Engineering Service
# ============================================================
# Coordinates dataset generation for a specific project.
# ============================================================
import json
import uuid
from pathlib import Path
import networkx as nx
from loguru import logger
from datetime import datetime, timezone

from feature_engineering.dataset.builder import GraphDatasetBuilder
from feature_engineering.dataset.serializer import save_graph, validate_graph

class FeatureService:
    def __init__(self, use_mock_codebert: bool = True):
        self.builder = GraphDatasetBuilder(use_mock_codebert=use_mock_codebert)
    
    def process_project(self, project_id: str, graphs_dir: Path, output_dir: Path) -> dict:
        """Process all security_graph.json files in a project into .pt tensors."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        valid_graphs = 0
        invalid_graphs = 0
        
        # In a real batch script, we would iterate through all graphs in the directory
        # Here we just look for all `security_graph.json` files recursively
        for graph_file in graphs_dir.rglob("security_graph.json"):
            try:
                data = json.loads(graph_file.read_text(encoding="utf-8"))
                
                # Load NetworkX DiGraph
                cpg = nx.DiGraph()
                for node in data.get("nodes", []):
                    nid = node.pop("id")
                    cpg.add_node(nid, **node)
                for edge in data.get("edges", []):
                    src = edge.pop("source")
                    tgt = edge.pop("target")
                    cpg.add_edge(src, tgt, **edge)
                
                # Mock Label: Since we don't have vulnerability labels assigned yet
                # We'll assign safe=0 by default or extract from metadata if available
                label = 0
                
                pyg_data = self.builder.build_from_networkx(cpg, label=label)
                
                if validate_graph(pyg_data):
                    pt_filename = f"{graph_file.parent.name}_{uuid.uuid4().hex[:8]}.pt"
                    save_graph(pyg_data, str(output_dir / pt_filename))
                    valid_graphs += 1
                else:
                    invalid_graphs += 1
                    
            except Exception as e:
                logger.error(f"Failed to process graph {graph_file}: {e}")
                invalid_graphs += 1

        return {
            "processed": valid_graphs,
            "failed": invalid_graphs,
            "total": valid_graphs + invalid_graphs,
            "dataset_path": str(output_dir)
        }
