import yaml
from jinja2 import Template
import argparse
import sys
import os


def generate_mermaid_from_yaml(yaml_file, output_file):
    #Try to open up the file where avd_group vars are located.
    try:
        with open(yaml_file, "r") as f:
            network_data = yaml.safe_load(f)
        #Empty dicts + lists for the elements
        devices = {}
        connections = []
        mlag_connections = []
        # A bunch of itterating through the data in python sigh. 
        for spine_node in network_data.get("spine", {}).get("nodes", []):
            devices[spine_node["name"]] = {"label": spine_node["name"], "type": "Router"}
        for l3leaf_group in network_data.get("l3leaf", {}).get("node_groups", []):
            for node in l3leaf_group.get("nodes", []):
                devices[node["name"]] = {"label": node["name"], "type": "L3Leaf"}
        for l2leaf_group in network_data.get("l2leaf", {}).get("node_groups", []):
            for node in l2leaf_group.get("nodes", []):
                devices[node["name"]] = {"label": node["name"], "type": "L2Leaf"}

        # Getting all the connections
        for spine_node in network_data.get("spine", {}).get("nodes", []):
            spine_name = spine_node["name"]
            for l3leaf_group in network_data.get("l3leaf", {}).get("node_groups", []):
                for leaf_node in l3leaf_group.get("nodes", []):
                    leaf_name = leaf_node["name"]
                    for uplink_interface in leaf_node.get("uplink_switch_interfaces", []):
                        connections.append(
                            {"source": leaf_name, "target": spine_name, "label": f"{leaf_name}-{uplink_interface} - {spine_name}-{uplink_interface}"}
                        )

        for l2leaf_group in network_data.get("l2leaf", {}).get("node_groups", []):
            for leaf_node in l2leaf_group.get("nodes", []):
                leaf_name = leaf_node["name"]
                for uplink_switch in network_data["l2leaf"]["defaults"]["uplink_switches"]:
                    for uplink_interface in leaf_node.get("uplink_switch_interfaces", []):
                        connections.append(
                            {"source": leaf_name, "target": uplink_switch, "label": f"{leaf_name}-{uplink_interface} - {uplink_switch}-{uplink_interface}"}
                        )
        # Getting MLAG connections
        for group in network_data.get("l3leaf", {}).get("node_groups", []) + network_data.get("l2leaf", {}).get("node_groups", []):
            for node_index in range(0, len(group["nodes"]), 2):
                if node_index + 1 < len(group["nodes"]):
                    node1_name = group["nodes"][node_index]["name"]
                    node2_name = group["nodes"][node_index + 1]["name"]
                    mlag_interfaces = network_data.get("l3leaf", {}).get("defaults", {}).get("mlag_interfaces", []) or network_data.get("l2leaf", {}).get("defaults", {}).get("mlag_interfaces", [])
                    for mlag_interface in mlag_interfaces:
                        connections.append(
                            {"source": node1_name, "target": node2_name, "label": f"{node1_name}-{mlag_interface} - {node2_name}-{mlag_interface}"}
                        )

        # Creating Jinja2 
        mermaid_template = """
        graph TD
            {% for device_id, device_data in devices.items() %}
            {{ device_id }}[{{ device_data.label }}];
            {% endfor %}
            {% for connection in connections %}
            {{ connection.source }} -- {{ connection.label }} --> {{ connection.target }};
            {% endfor %}
            {% for device_id, device_data in devices.items() %}
            style {{ device_id }} fill:#00008B,stroke:#333,stroke-width:2px
            {% endfor %}
        """

        # Render the template
        template = Template(mermaid_template)
        mermaid_code = template.render(devices=devices, connections=connections, mlag_connections=mlag_connections)

        # Output the Mermaid code to a file
        with open(output_file, "w") as f:
            f.write(f"```mermaid\n{mermaid_code}\n```")
        print(f"Mermaid code written to {output_file}")

    except FileNotFoundError:
        print(f"Error: YAML file '{yaml_file}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)



def main():
    """
    Main function to parse arguments and generate the Mermaid diagram.
    """
    parser = argparse.ArgumentParser(description="Generate Mermaid diagram from YAML.")
    parser.add_argument(
        "--yaml_file",
        "-y",
        default="group_vars/DC1_FABRIC.yaml",
        help="Path to the input YAML file.",
    )
    parser.add_argument(
        "--output_file",
        "-o",
        default="avddiagram.md",
        help="Path to the output Markdown file.",
    )

    args = parser.parse_args()
    yaml_file = args.yaml_file
    output_file = args.output_file
    if not os.path.exists(args.yaml_file):
        print(f"Error: YAML file not found at {args.yaml_file}")
        sys.exit(1)
    generate_mermaid_from_yaml(yaml_file, output_file)



if __name__ == "__main__":
    main()
