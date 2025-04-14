"""
Merkle Tree Visualizer.
"""

import streamlit as st
import hashlib
import graphviz
import json
import time
import os
from typing import List, Optional, Dict
from dataclasses import dataclass

# --- Constants ---
HASH_ALGORITHM = hashlib.sha256
NODE_HASH_TRUNCATE_LENGTH = 8
MAX_LEAVES_WARNING = 1000

# --- Data Classes ---
@dataclass
class MerkleProof:
    """Represents proof of inclusion in a Merkle Tree."""
    siblings: List[str]
    path_indices: List[int]

# --- Core Merkle Tree Logic ---
class MerkleTree:
    """Implements a Merkle Tree with cryptographic proofs."""
    def __init__(self):
        self.leaf_data: List[str] = []
        self.tree_layers: List[List[str]] = []
        self.root: Optional[str] = None
        self._hash_cache: Dict[str, str] = {}

    def _hash_with_cache(self, data: str) -> str:
        """Computes SHA256 hash with caching."""
        if data not in self._hash_cache:
            self._hash_cache[data] = HASH_ALGORITHM(data.encode()).hexdigest()
        return self._hash_cache[data]

    def add_data(self, data_list: List[str]) -> None:
        """Adds data and rebuilds tree."""
        self.leaf_data = data_list
        self._build_tree()

    def _build_tree(self) -> None:
        """Constructs Merkle Tree layers."""
        self.tree_layers = []
        self.root = None
        self._hash_cache = {}

        if not self.leaf_data:
            return

        # Build with progress feedback
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Leaf layer
        status_text.text("Hashing leaf data...")
        leaves = [self._hash_with_cache(data) for data in self.leaf_data]
        self.tree_layers.append(leaves.copy())
        progress_bar.progress(10)

        # Intermediate layers
        current_layer = leaves
        layer_count = 0
        while len(current_layer) > 1:
            layer_count += 1
            status_text.text(f"Building layer {layer_count}...")

            if len(current_layer) % 2 == 1:
                current_layer.append(current_layer[-1])

            next_layer = []
            for i in range(0, len(current_layer), 2):
                combined = current_layer[i] + current_layer[i+1]
                next_layer.append(self._hash_with_cache(combined))

            self.tree_layers.insert(0, next_layer.copy())
            current_layer = next_layer
            progress = min(10 + (layer_count * 80 // len(self.leaf_data)), 90)
            progress_bar.progress(progress)

        self.root = self.tree_layers[0][0] if self.tree_layers else None
        status_text.text("Tree construction complete!")
        progress_bar.progress(100)
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

    def generate_proof(self, index: int) -> Optional[MerkleProof]:
        """Generates inclusion proof for given index."""
        if self.root is None or not (0 <= index < len(self.leaf_data)):
            return None

        siblings = []
        path_indices = []
        current_index = index

        for layer_idx in range(len(self.tree_layers)-1, 0, -1):
            current_layer = self.tree_layers[layer_idx]
            is_left = current_index % 2 == 0
            path_indices.append(0 if is_left else 1)

            sibling_index = current_index + 1 if is_left else current_index - 1
            if sibling_index < len(current_layer):
                siblings.append(current_layer[sibling_index])
            elif is_left and len(current_layer) % 2 == 1 and current_index == len(current_layer)-1:
                siblings.append(current_layer[current_index])

            current_index = current_index // 2

        return MerkleProof(siblings, path_indices)

    def verify_proof(self, data: str, proof: MerkleProof) -> bool:
        """Verifies proof against stored root."""
        if self.root is None or not proof:
            return False

        current_hash = self._hash_with_cache(data)
        for i, sibling in enumerate(proof.siblings):
            combined = current_hash + sibling if proof.path_indices[i] == 0 else sibling + current_hash
            current_hash = self._hash_with_cache(combined)
        return current_hash == self.root

# --- Visualization ---
class MerkleVisualizer:
    @staticmethod
    def render(tree_layers: List[List[str]]) -> graphviz.Digraph:
        """Creates Graphviz Visualization."""
        if not tree_layers:
            return graphviz.Digraph()

        dot = graphviz.Digraph(comment='Merkle Tree')
        dot.attr(rankdir='TB')
        layer_node_ids = []

        for layer_idx, layer in enumerate(tree_layers):
            current_layer_ids = []
            for node_idx, hash_val in enumerate(layer):
                node_id = f"L{layer_idx}_N{node_idx}"
                label = f"{hash_val[:NODE_HASH_TRUNCATE_LENGTH]}..."
                if layer_idx == len(tree_layers)-1:
                    dot.node(node_id, label, shape='box')
                else:
                    dot.node(node_id, label)
                current_layer_ids.append(node_id)
            layer_node_ids.append(current_layer_ids)

        for layer_idx in range(len(tree_layers)-1):
            for node_idx, parent_id in enumerate(layer_node_ids[layer_idx]):
                left = node_idx * 2
                right = left + 1
                children = layer_node_ids[layer_idx+1]
                if left < len(children):
                    dot.edge(parent_id, children[left])
                if right < len(children):
                    dot.edge(parent_id, children[right])

        return dot

# --- Streamlit Application ---
def initialize_app_state():
    """Initializes session state."""
    if 'merkle_tree' not in st.session_state:
        st.session_state.merkle_tree = MerkleTree()
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = MerkleVisualizer()
    if 'tree_graph' not in st.session_state:
        st.session_state.tree_graph = None

def export_tree_data(tree: MerkleTree) -> dict:
    """Exports tree data as JSON-serializable dict."""
    return {
        'leaf_data': tree.leaf_data,
        'tree_layers': tree.tree_layers,
        'root': tree.root
    }

def main():
    """Main application interface."""
    st.set_page_config(page_title="Merkle Tree Visualizer", layout="wide")
    st.title("🌳 Merkle Tree Visualizer")

    initialize_app_state()
    tree = st.session_state.merkle_tree
    visualizer = st.session_state.visualizer

    # --- Data Input Section ---
    st.subheader("Step 1: Input Data and Build Tree")
    with st.expander("Please proceed with the first requirement for Merkle Tree Visualization:", expanded=True):
        input_data = st.text_area(
            "Enter data blocks (one per line):",
            height=150,
            help="Each line becomes a leaf node. Large trees (>1000 leaves) may take longer to build."
        )

        if st.button("Build/Update Merkle Tree"):
            data_blocks = [line for line in input_data.splitlines() if line.strip()]
            if data_blocks:
                if len(data_blocks) > MAX_LEAVES_WARNING:
                    st.warning(f"Building large tree with {len(data_blocks)} leaves. This may take a while...")

                with st.spinner("Constructing Merkle tree..."):
                    tree.add_data(data_blocks)
                    st.session_state.tree_graph = visualizer.render(tree.tree_layers)

                st.success(f"Tree constructed with {len(data_blocks)} leaves!")
            else:
                tree.add_data([])
                st.session_state.tree_graph = None
                st.warning("Input data is empty. Tree cleared.")

    # --- Tree Visualization Section ---
    if tree.root:
        st.markdown("---")
        st.subheader("Step 2: Tree Visualization")

        # Export Controls
        col1, col2 = st.columns([4, 1])
        with col2:
            st.write("### Export Options")
            if st.button("Export Tree as JSON"):
                tree_data = export_tree_data(tree)
                st.download_button(
                    label="Download JSON",
                    data=json.dumps(tree_data, indent=2),
                    file_name="merkle_tree.json",
                    mime="application/json"
                )

            if st.session_state.tree_graph:
                if st.button("Export Visualization as PNG"):
                    try:
                        st.session_state.tree_graph.format = 'png'
                        st.session_state.tree_graph.render('merkle_tree')
                        with open("merkle_tree.png", "rb") as f:
                            st.download_button(
                                label="Download PNG",
                                data=f,
                                file_name="merkle_tree.png",
                                mime="image/png"
                            )
                        os.remove("merkle_tree.png")
                    except Exception as e:
                        st.error(f"Export failed: {str(e)}")

        with col1:
            if st.session_state.tree_graph:
                st.graphviz_chart(st.session_state.tree_graph)
            else:
                st.warning("Visualization not available!")

        # Tree Metadata
        st.write("#### Root Hash")
        st.code(tree.root, language='text')

        st.write("### Tree Information")
        cols = st.columns(3)
        cols[0].metric("Leaf Count", len(tree.leaf_data))
        cols[1].metric("Tree Depth", len(tree.tree_layers))

        # --- Proof Verification Section ---
        st.markdown("---")
        st.subheader("Step 3: Proof Verification")

        if tree.leaf_data:
            verify_data = st.selectbox(
                "Select data to verify:",
                options=tree.leaf_data,
                index=0
            )

            if st.button("Generate & Verify Proof"):
                with st.spinner("Generating proof..."):
                    index = tree.leaf_data.index(verify_data)
                    proof = tree.generate_proof(index)

                if proof:
                    st.success("Proof generated successfully!")

                    # Display proof details without expander
                    st.write("#### Proof Details")
                    st.json({
                        "Data": verify_data,
                        "Index": index,
                        "Sibling Hashes": [h[:12] + "..." for h in proof.siblings],
                        "Path Indices": proof.path_indices
                    })

                    with st.spinner("Verifying proof..."):
                        is_valid = tree.verify_proof(verify_data, proof)

                    if is_valid:
                        st.success("PROOF IS VALID!")
                    else:
                        st.error("PROOF VERFICATION FAILED!")
                else:
                    st.error("FAILED TO GENERATE PROOF!")
        else:
            st.info("NO DATA IN TREE TO VERIFY!")

if __name__ == "__main__":
    main()
