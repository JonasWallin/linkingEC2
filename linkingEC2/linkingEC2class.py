from __future__ import print_function
from .linkingEC2 import *
import boto.ec2
import os

class LinkingHandler(object):
	"""
		class for automatically setting up a cluster on EC2 
		distributing packages and simplifing for openmpi
		
		only tested for ubuntu machines on EC2
		
		always remeber to terminate!!!
	"""
	
	
	def __init__(self, aws_secret_access_key, aws_access_key_id, aws_region_name, key_name, key_location
			   , processes = None):
		"""
			*aws_region_name*	   which region one is loging into
			*key_location*		  where on has the key to ssh into EC2
			*key_name*			  what is the keyname 
			*aws_secret_access_key* to log into amazon
			*aws_access_key_id*	 to log into amazon
		*processes*			 number of processes allowed to be used
			
		"""
		
		self.my_key_location	   = key_location
		self.aws_secret_access_key = aws_secret_access_key
		self.aws_access_key_id	 = aws_access_key_id
		self.aws_region_name	   = aws_region_name
		self.key_name			  = key_name

		self.conn = boto.ec2.connect_to_region( self.aws_region_name,
								  aws_access_key_id				= self.aws_access_key_id,
								  aws_secret_access_key			= self.aws_secret_access_key)


		self.reservation   			= None
		self.nodes		 			= None
		self.silent					= False
		self.test		  			= False
		self.user		  			= 'ubuntu'
		self.pip_installed 			= False
		self.apt_update				= False
		self.processes	 			= processes
		self.spotprice_reservation  = []
		self._shutdown_if_exit      = True # if false won't close the cluster when object is destroyed
		

	def __del__(self):
		
		if self._shutdown_if_exit:
			self.terminate_cluster()


	def connect_cluster(self, first_time =True):
		"""
			Connecting to an alredy started cluster
			*get_n*	  - get number of processes for each node
			*first_time* - if the cluster has not been setup before
		"""
		
		self.reservation = self.conn.get_all_reservations()[0]
		
		self.nodes = get_dns_name(self.reservation, self.conn, silent = self.silent)
		
		self.setup_cluster(get_n = True, first_time = first_time)	


	def connect_spot_instances(self, first_time =True):
		"""
			Connect to spot instances 
			
			*get_n*      collect number of process for the nodes
			*first_time* build up the basic structure
			
		"""
		
		self.spotprice_reservation = self.conn.get_all_spot_instance_requests()
		for i,spot in enumerate(self.spotprice_reservation):
			if spot.instance_id is not None:
				res = self.conn.get_all_instances(instance_ids=[spot.instance_id])
				node_alias  = 'node{0:03d}'.format(i+1)
				self.reservation.append(res[0].instances[0])
				public_dns  = res[0].instances[0].public_dns_name
				private_dns = res[0].instances[0].private_dns_name
				private_ip_address = res[0].instances[0].private_ip_address
				self.nodes.append({'name'  :node_alias,
							 'public_dns' :public_dns,
							  'private_dns':private_dns,
							 'private_ip' :private_ip_address})
		
													
		
		self.setup_cluster(get_n = True, first_time = first_time)		
					
					
	def setup_cluster(self, get_n = True, first_time = True):
		'''
			building copying files and adding ssh keys to all nodes
			this function is for helping the MPI to work across nodes
			*get_n*        - collect number of processes each node has
			*first_time*   - should we running things? (if first_time is false we do bascilly notihng)
		'''		
		
		if get_n:
			get_number_processes(nodes  = self.nodes,
								 my_key =  self.my_key_location,
								 user   = self.user,
								 silent = self.silent)	
		if first_time:
			self.copy_files_to_nodes(file_name = self.my_key_location, 
									 destination = '~/.ssh/id_rsa')
			self._ssh_disable_StrictHostKeyChecking()
			#copy_file_to_nodes(nodes = self.nodes, 
			#				   file_location = self.my_key_location, 
			#				   destination = '~/.ssh/id_rs',
			#				   my_key = self.my_key_location)
						
			self.setup_nodefile()	
		
					
	def start_cluster(self, instance, instance_type, security_groups, count = 1,
					  extra_build = True):
		"""
			starting up a cluster
			*instance*		what operating system(?) to use like 'ami-d05e75b8'
			*instace_type*	what type like 't2.micro'
			*security_groups* a security group needs to be set
			*count*		   number of nodes
			*extra_build*	 checking that ssh works, adds ssh keys to all nodes
							  fixing node lists  
		"""
		
		self.reservation = self.conn.run_instances( instance,
													key_name		= self.key_name,
													instance_type   = instance_type,
													security_groups = security_groups,
													min_count = count,
													max_count = count)
													
		self.nodes = get_dns_name(self.reservation, self.conn, silent = self.silent)
		
		self.setup_cluster(get_n = True, first_time = extra_build)
		
	def _ssh_disable_StrictHostKeyChecking(self):
		"""
			disable StrictHostKeyChecking in the first node
		"""
		if not self.silent:
			print("disable StrictHostKeyChecking  in {name}:".format(name = self.nodes[0]['name']),end='')
			sys.stdout.flush()		


		create_file_to_nodes(nodes		 = self.nodes[0], 
						   file_name	   = '~/.ssh/config', 
						   file_content	= 'StrictHostKeyChecking no',
						   my_key		  = self.my_key_location,
						   user			= self.user,
						   silent		  = True)

	
	
	def copy_files_from_node(self, file_name, destination = os.curdir, node = None):
		
		
		if node is None:
			node = self.nodes[0]
		else:
			node = self.nodes[node]
			
		copy_file_from_node(node = node, 
						   file_location = file_name, 
						   destination = destination,
						   my_key		= self.my_key_location,
						   user		  = self.user,
						   silent		= self.silent)
		
	def copy_files_to_nodes(self,  file_name, destination = '~/',	  nodes = None):
		"""
			copying {file_name} to {destination} in {nodes}
			*file_name*   name of files to be copied
			*destination* where to put the file 
			*nodes*	   int or list of inte which nodes to copy
		"""
		nodes_to_copy_to = self._intlist_to_nodes(nodes)
		copy_file_to_nodes(nodes		 = nodes_to_copy_to, 
						   file_location = file_name, 
						   destination   = destination,
						   my_key		= self.my_key_location,
						   user		  = self.user,
						   silent		= self.silent)


	def setup_nodefile(self):
		""" setting up nodefile for mpi and /etc/hosts/ to go with it"""
		NODE_STRING = ''
		HOST_STRING = ''
		for node in self.nodes:
			NODE_STRING += '{name} slots={n_processes}\n'.format(	 name = node['name'],
														n_processes = node['n_process']) 
			HOST_STRING += '{ip} {name}\n'.format(name = node['name'], ip = node['private_ip'])
		
		NODE_STRING = NODE_STRING[:-1]
		HOST_STRING = HOST_STRING[:-1]
		create_file_to_nodes(self.nodes[0], file_content = NODE_STRING,
							 file_name = '~/nodefile', 
							 my_key = self.my_key_location, 
							 test=self.test) 
		
		create_file_to_nodes(self.nodes[0], 
							 file_content = HOST_STRING,
							 file_name = '/etc/hosts',
							 my_key = self.my_key_location, 
							 test=self.test,
							 sudo=True) 


	def _intlist_to_nodes(self, int_list):
		"""
			from a list of inte (or int) creates a list
			of nodes
		"""
		if int_list == None:
			int_list = range(len(self.nodes))
		elif not isinstance(int_list, list):
			int_list = [int_list]
			
		nodes = [self.nodes[i] for i in int_list]
		return nodes
		
	def get_ssh_login(self, node = 0):
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
				   low	= 0,
				   high   =  len(self.reservation.instances) ) 
				  )
		
		return( "ssh  -i {keyloc} -o 'StrictHostKeyChecking no'  ubuntu@{hostname}".format(
		keyloc = self.my_key_location,
		hostname =  self.nodes[node]['public_dns']))
		
		
	def terminate_cluster(self):
		"""
			closes down the cluster!
		"""
		
		for spot_instance in self.spotprice_reservation:
			self.conn.cancel_spot_instance_requests(spot_instance)
		
		for i in range(len(self.reservation.instances)):
			self.reservation.instances[i].terminate()
	
	
	def pip_install(self, packages, nodes = None):
		"""		
			installing python through pip install to nodes
			*packages* list or string of packages to be installed
			*nodes*	list of ints install package on nodes if none install
						on all nodes
		"""
		res = -1
		
		if self.pip_installed == False:
			res = self.apt_install('python-pip')
			
			if res == 0:
				self.pip_installed = True
		
		if self.pip_installed:
			
			nodes_to_install_to = self._intlist_to_nodes(nodes)
			
			res = import_package_to_nodes(packages = packages, 
										  method = 'pip',
										  nodes = nodes_to_install_to,
										  my_key = self.my_key_location,
										  silent = self.silent,
										  user   = self.user,
										  processes = self.processes)
		return res
	
	def apt_install(self, packages, nodes = None):
		"""
			installing packages through apt-get install to nodes
			*packages* list or string of packages to be installed
			*nodes*	list of ints install package on nodes if none install
						on all nodes
		"""
		
		
		
		res = -1
		
		if not self.apt_update:
			res = update_apt_get_to_nodes(nodes = self.nodes,
										 my_key = self.my_key_location,
										 silent = self.silent,
										 user   = self.user,
										 processes = self.processes
										 )
			if res == 0:
				self.apt_update	= True	  
		
		if  self.apt_update:
			
			nodes_to_install_to  = self._intlist_to_nodes(nodes)
			
			res = import_package_to_nodes(packages = packages, 
									nodes = nodes_to_install_to,
									my_key = self.my_key_location,
									silent = self.silent,
									user   = self.user,
									processes = self.processes
									)
		return res
			
	
	def send_command_ssh(self, command, nodes = None, silent = False):
		"""
			send *command* to *nodes* through ssh
		"""
		
		nodes_to_ssh = self._intlist_to_nodes(nodes)		
		os_res = 0
	
		for node in nodes_to_ssh: 
		
			if not self.silent:
				print('{node}, sshing in  {command} '.format(node = node['name'], 
										 command = command))
				sys.stdout.flush()

			input_string = "ssh  -i {keyloc} -o 'StrictHostKeyChecking no'  {user}@{hostname} '{command}'".format(
							keyloc   = self.my_key_location,
							user	 = self.user,
							hostname =  node['public_dns'],
							command  = command)  
							
			os_res = os.system(input_string)
			
			
			
			if os_res != 0:

				if not self.silent:
					print('{node} failed: \n {in_string}'.format(node = node['name'],
											 in_string =input_string))
					sys.stdout.flush()
				return os_res
			
			if not self.silent:
				print('{node} done'.format(node = node['name']))
				sys.stdout.flush()
		return os_res
		
	def test_ssh_in(self):
		"""
			testing starting the ssh making sure things works!
		"""
		
		message = 'in the node'
		if self.silent:
			message = ''
		for node in self.nodes: 
		
			if not self.silent:
				print("checking if ssh into {name} works:".format(name = node['name']))
				sys.stdout.flush()
			_counter = 0
			input_string = "ssh  -i {keyloc} -o 'StrictHostKeyChecking no'  {user}@{hostname} 'echo {message}'".format(
							keyloc   = self.my_key_location,
							user	 = self.user,
							hostname =  node['public_dns'],
							message  = message)
							
					
			os_res = 1
			while os_res != 0:
				
				if not self.silent:
					print('*', end = '')
					sys.stdout.flush()
					
				os_res = os.system(input_string)
				_counter += 1
				sleep(10)
				
				if _counter > 5:
					print('\n' + input_string)
					sleep(20)
					sys.stdout.flush()
					raise IOError('Failed to connect to {name}'.format(name = node['name']))
			if not self.silent:
				print('')
		