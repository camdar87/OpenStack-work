import argparse
from openstack import connection
from openstack.exceptions import BadRequestException
import openstack

def create():
    # Establish a connection to Catalyst Cloud
    conn = connection.Connection(
        cloud='catalystcloud',
        config_file='clouds.yaml',
    )

    subnet = None  # Default value for subnet

    # Check if the network already exists
    existing_networks = conn.network.networks(name='dargcl1-net')
    network = next(existing_networks, None)  # Get the first network or None if it doesn't exist

    if network:
        print("Network 'dargcl1-net' already exists.")
    else:
        # Define the network parameters
        network_name = 'dargcl1-net'
        ip_range = '192.168.50.0/24'

        # Create the network
        network = conn.network.create_network(name=network_name)

        # Create the subnet within the network
        subnet = conn.network.create_subnet(
            name='dargcl1-subnet',
            network_id=network.id,
            cidr=ip_range,
            ip_version=4,
        )

        print("Created Network 'dargcl1-net'.")

    # Check if the router already exists
    existing_routers = conn.network.routers(name='dargcl1-rtr')
    router = next(existing_routers, None)  # Get the first router or None if it doesn't exist

    if router:
        print("Router 'dargcl1-rtr' already exists.")
    else:
        # Define the router name
        router_name = 'dargcl1-rtr'

        # Find the public network by name ("public-net")
        public_network_name = 'public-net'
        public_net = conn.network.find_network(public_network_name)

        # Create the router and specify the public network for the gateway
        router = conn.network.create_router(name=router_name, external_gateway_info={'network_id': public_net.id})

        # Add the subnet to the router interface
        if subnet:  # Check if subnet is defined
            conn.network.add_interface_to_router(router, subnet_id=subnet.id)
            print("Created Router 'dargcl1-rtr' and added subnet.")
        else:
            print("Error: Subnet not found.")

        # Create a floating IP on the public network
        public_network_name = 'public-net'
        public_network = conn.network.find_network(public_network_name)

        try:
            floating_ip = conn.network.create_ip(floating_network_id=public_network.id)
            print("Floating IP created:", floating_ip.floating_ip_address)
        except openstack.exceptions.BadRequestException as e:
            print(f"Error creating floating IP: {e}")




    # Find the security group by name
    security_group_name = 'default'
    security_groups = conn.network.security_groups(name=security_group_name)

    if security_groups:
        security_group = next(security_groups)
        security_group_id = security_group.id
        print(f"Found security group '{security_group_name}' with ID: {security_group_id}")
    else:
        print(f"Security group '{security_group_name}' not found.")

# Constants for image and flavor names
    IMAGE_NAME = "ubuntu-minimal-22.04-x86_64"
    FLAVOR_NAME = "c1.c1r1"
    NETWORK_NAME = "dargcl1-net"  # Replace with your network name
    SERVER_NAMES = ['dargcl1-web', 'dargcl1-app', 'dargcl1-db']

    # Check if the network already exists
    existing_networks = conn.network.networks(name=NETWORK_NAME)
    network = next(existing_networks, None)  # Get the first network or None if it doesn't exist

    if network:
        print(f"Using existing network: {NETWORK_NAME}")
    else:
        print(f"Network '{NETWORK_NAME}' not found. Please create the network.")
        return

    # Find the security group by name
    security_group_name = 'default'
    security_groups = conn.network.security_groups(name=security_group_name)

    if security_groups:
        security_group = next(security_groups)
        security_group_id = security_group.id
        print(f"Found security group '{security_group_name}' with ID: {security_group_id}")
    else:
        print(f"Security group '{security_group_name}' not found.")

    for vm_name in SERVER_NAMES:
        image = conn.compute.find_image(IMAGE_NAME)
        flavor = conn.compute.find_flavor(FLAVOR_NAME)

        # Create server with the current VM name
        server = conn.compute.create_server(
            name=vm_name, image_id=image.id, flavor_id=flavor.id,
            networks=[{"uuid": network.id}], key_name='cameronKey',
            security_groups=[{"name": "default"}])  # Assigning the security group

        # Wait for server creation
        server = conn.compute.wait_for_server(server)

        # Assign the floating IP to the web server
        if vm_name == 'dargcl1-web':
            public_network_name = 'public-net'
            public_network = conn.network.find_network(public_network_name)
            floating_ips = conn.network.ips(network_id=public_network.id, status='DOWN')
            floating_ip = next(floating_ips, None)
            if floating_ip:
                conn.compute.add_floating_ip_to_server(server, floating_ip.floating_ip_address)
                print(f"Assigned Floating IP {floating_ip.floating_ip_address} to '{vm_name}'.")
            else:
                print("No available Floating IP to assign.")




def run():
    pass

def stop():
    pass



def destroy():
    # Import the openstack module within the function
    import openstack

    # Establish a connection to Catalyst Cloud 
    conn = openstack.connection.Connection(
        cloud='catalystcloud',
        config_file='clouds.yaml',
    )

    # Find the floating IP by name or ID
    floating_ip = conn.network.find_ip(name_or_id='floating_ip')  # Update with correct name or ID
    if floating_ip:
        # Deallocate the floating IP
        try:
            conn.network.deallocate_ip(floating_ip)
            print("Deallocated Floating IP.")
        except openstack.exceptions.SDKException as e:
            print(f"Failed to deallocate Floating IP: {e}")

    # Delete the servers
    server_names = ['dargcl1-web', 'dargcl1-app', 'dargcl1-db']
    for server_name in server_names:
        existing_servers = conn.compute.servers(name=server_name)
        server = next(existing_servers, None)  # Get the first server or None if it doesn't exist
        if server:
            conn.compute.delete_server(server)
            print(f"Deleted Server '{server_name}'.")
        else:
            print(f"Server '{server_name}' does not exist.")

    # Delete the router
    router = conn.network.find_router(name_or_id='dargcl1-rtr')
    if router:
        # Clear router interfaces to force deletion
        for port in conn.network.ports(device_id=router.id):
            conn.network.remove_interface_from_router(router, port_id=port.id)
        # Now delete the router
        try:
            conn.network.delete_router(router.id)
            print("Deleted Router 'dargcl1-rtr'.")
        except openstack.exceptions.SDKException as e:
            print(f"Failed to delete Router 'dargcl1-rtr': {e}")

    # Delete the subnet
    subnet = conn.network.find_subnet(name_or_id='dargcl1-subnet')
    if subnet:
        conn.network.delete_subnet(subnet.id)
        print("Deleted Subnet 'dargcl1-subnet'.")
    else:
        print("Subnet 'dargcl1-subnet' does not exist.")

    # Delete the network
    network = conn.network.find_network(name_or_id='dargcl1-net')
    if network:
        conn.network.delete_network(network.id)
        print("Deleted Network 'dargcl1-net'.")
    else:
        print("Network 'dargcl1-net' does not exist.")

# Rest of the code remains unchanged




def status():
    pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', help='One of "create", "run", "stop", "destroy", or "status"')
    args = parser.parse_args()
    operation = args.operation

    operations = {
        'create'  : create,
        'run'     : run,
        'stop'    : stop,
        'destroy' : destroy,
        'status'  : status
    }

    action = operations.get(operation, lambda: print('{}: no such operation'.format(operation)))
    action()

