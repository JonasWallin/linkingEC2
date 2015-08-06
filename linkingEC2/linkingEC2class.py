from .linkingEC2 import *
import boto.ec2

class LinkingHandler(object):
	"""
		class for automatically setting up a cluster on EC2 
		distributing packages and simplifing for openmpi
		
		only tested for ubuntu machines on EC2
		
		always remeber to terminate!!!
	"""
	
	
	def __init__(self, aws_secret_access_key, aws_access_key_id, region_name, key_location):
		"""
			*region_name*           which region one is loging into
			*key_location*          where on has the key to ssh into EC2
			*aws_secret_access_key* to log into amazon
			*aws_access_key_id*     to log into amazon
			
		"""
		
		self.my_key_location = key_location
		self.aws_secret_access_key = aws_secret_access_key
		self.aws_access_key_id  = aws_access_key_id
		self.region_name = region_name

		self.conn = boto.ec2.connect_to_region(         = self.aws_region_name,
                                  aws_access_key_id     = self.acess_key_id,
                                  aws_secret_access_key = self.aws_secret_key)


		self.reservation = None
		self.nodes       = None
		self.silent      = False
		self.test        = False
		self.user        = 'ubuntu'
		

	def start_cluster(instance, instance_type, security_groups, count = 1)
		"""
			starting up a cluster
			*instance*        what operating system(?) to use like 'ami-d05e75b8'
			*instace_type*    what type like 't2.micro'
			*security_groups* a security group needs to be set
			*count*           number of nodes
		"""
		
		self.reservation = self.conn.run_instances(instance,
													instance_type,
													security_groups,
													min_count = count,
													max_count = count)
													
		self.nodes = get_dns_name(self.reservation, self.conn, silent = self.silent)
		get_number_processes(nodes  = self.nodes,
							 my_key =  self.my_key_location,
							 user   = self.user
							 silent = self.silent)
		
	def get_ssh_login(node = 0)
		"""
			get the command to ssh into the nodes
			*node* number of the node to ssh into
		"""
		
		
		if self.nodes  == None:
			print("need to start cluster")
			return
		
		if node < 0 or node >= len(self.reservation.instances):
			print("node {number} does not exists choose between [{low} {high}]".format(
				   number = node,
				   low    = 0,
				   high   =  len(self.reservation.instances) ) 
				  )
		
		return( "ssh  -i {keyloc} -o 'StrictHostKeyChecking no'  ubuntu@{hostname}".format(
        keyloc = my_key_loc,
        hostname =  self.nodes[node]['public_dns']))
		
		
		
		
		
		
		
		
		