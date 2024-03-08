import geni.portal as portal
import geni.rspec.pg as pg
import geni.rspec.igext as IG

pc = portal.Context()

# Define parameters for both clusters
pc.defineParameter("n1", "Number of nodes in Cluster 1 (2)",
                   portal.ParameterType.INTEGER, 2)
pc.defineParameter("n2", "Number of nodes in Cluster 2 (3 or 4)",
                   portal.ParameterType.INTEGER, 3)
pc.defineParameter("userid", "CloudLab user ID to deploy K8s from (should be your CloudLab ID. Defaulted to none",
                   portal.ParameterType.STRING, 'none')
pc.defineParameter("corecount", "Number of cores in each node.  NB: Make certain your requested cluster can supply this quantity.",
                   portal.ParameterType.INTEGER, 4)
pc.defineParameter("ramsize", "MB of RAM in each node.  NB: Make certain your requested cluster can supply this quantity.",
                   portal.ParameterType.INTEGER, 4096)
params = pc.bindParameters()

request = pc.makeRequestRSpec()

tourDescription = """
This profile provides the template for Docker and Rancher/RKE2 Kubernetes installed on Ubuntu 22.04
"""

tour = IG.Tour()
tour.Description(IG.Tour.TEXT, tourDescription)
request.addTour(tour)

# Function to add nodes to a cluster
def add_cluster_nodes(cluster_name, num_nodes, start_ip):
    link = request.LAN(cluster_name + "_lan")
    for i in range(num_nodes):
        if i == 0:
            node = request.XenVM(cluster_name + "-head")
            bs_landing = node.Blockstore(cluster_name + "_bs_image", "/image")
            bs_landing.size = "500GB"
        else:
            node = request.XenVM(cluster_name + "-worker-" + str(i))
        node.cores = params.corecount
        node.ram = params.ramsize
        bs_landing = node.Blockstore(cluster_name + "_bs_" + str(i), "/image")
        bs_landing.size = "500GB"
        node.routable_control_ip = "true"
        node.disk_image = "urn:publicid:IDN+emulab.net+image+emulab-ops:UBUNTU22-64-STD"
        iface = node.addInterface("if" + str(i))
        iface.component_id = "eth1"
        iface.addAddress(pg.IPv4Address("192.168." + str(start_ip) + "." + str(i + 1), "255.255.255.0"))
        link.addInterface(iface)

        # install Docker
        node.addService(pg.Execute(shell="sh", command="sudo bash /local/repository/install_docker.sh"))
        # install Kubernetes
        node.addService(pg.Execute(shell="sh", command="sudo swapoff -a"))

        if i == 0:
            # install Kubernetes manager
            node.addService(pg.Execute(shell="sh", command="sudo bash /local/repository/kube_manager.sh " + params.userid + " " + str(num_nodes)))
            # install Helm
            node.addService(pg.Execute(shell="sh", command="sudo bash /local/repository/install_helm.sh"))
        else:
            node.addService(pg.Execute(shell="sh", command="sudo bash /local/repository/kube_worker.sh"))

# Add nodes to each cluster
add_cluster_nodes("cluster1", params.n1, 1)
add_cluster_nodes("cluster2", params.n2, 2)

pc.printRequestRSpec(request)
