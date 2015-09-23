from __future__ import print_function
import os
from time import sleep
import sys
import multiprocessing
import subprocess

def _remote(host, cmd='scp', user='root' , src=None  , dest=None,
		   credential=None, silent=False, test=False):
	"""ssh and scp to the amazon ec2
		taken and modfied from http://www.datawrangling.com/ (Pete Skomoroch)
	"""
	d = {
	'cmd'  : cmd ,
	'user' : user,
	'src'  : src ,
	'dest' : dest,
	'host' : host,
	}

	d['switches'] = ''
	if credential:
		d['switches'] = '-i %s' % credential

	if cmd == 'scp':

		template = '%(cmd)s %(switches)s -o "StrictHostKeyChecking no" %(src)s %(user)s@%(host)s:%(dest)s' 
	else:
		template = 'ssh	 %(switches)s -o "StrictHostKeyChecking no" %(user)s@%(host)s "%(cmd)s" '

	cmdline = template % d	 

	os_res = 0
	if not silent:
		print("\n{command}\n\n".format(command = cmdline))
	if not test:
		os_res = os.system(cmdline)
		
	return os_res


def get_dns_name(reservations, conn, silent = False):
	""" Gets the reservation public_dns and private dns_names
		reservation - object from conn.run_instances
	"""
	nodes = []
	for i in range(len(reservations.instances)):
		instance_id  = reservations.instances[i].id
		res = conn.get_all_instances(instance_ids=[instance_id])
		if not silent:
			print('waiting for instances {i}  to be running: \n'.format(i = i), end='')
			sys.stdout.flush()
			
		while( res[0].instances[0].update()=='pending'):
			sleep(5)
			print('*',end='')
			sys.stdout.flush()
		if not silent:
			print('\n')
		
		node_alias  = 'node{0:03d}'.format(i+1)
		public_dns  = res[0].instances[0].public_dns_name
		private_dns = res[0].instances[0].private_dns_name	
		private_ip_address = res[0].instances[0].private_ip_address
		
		
		nodes.append({'name'	   :	node_alias,
					  'public_dns' :	public_dns,
					  'private_dns':	private_dns,
					  'private_ip' :	private_ip_address})
	
	return nodes



def get_number_processes(nodes, my_key, user = 'ubuntu', silent=False):
	""" collects how many processes each node has in the clusters
		and appends it to the nodes
		*nodes*	- list from get_dns_names or single element from the same
		*user*	 - the amazon user (usually ubuntu or root)
		*my_key*   - location of the key
	"""
	
	input_command = " 'cat /proc/cpuinfo | grep processor | wc -l'"
	
	for node in nodes:
		
		if not silent:
			print('collecting {node} number of processes:'.format(node = node['name']), end='')
			sys.stdout.flush()
			
		input_string  = "ssh -i {key} -o 'StrictHostKeyChecking no' {user}@{host}".format(
		key = my_key,
		user = user,
		host = node['public_dns'])
		
		n_process = int(subprocess.check_output(input_string + input_command, shell=True, stderr=subprocess.STDOUT))
		node['n_process'] = n_process
		
		if not silent:
			print("done")


def _remote_on_node_wrapper(args):
	
	return(_remote_on_node(*args))
	
def _remote_on_node(node, silent, my_key, input_string, user, message = 'running '):
	""" Running the update on all system
	   
	   *node*		 - get_dns_names obj
	   *message*	  - print output	 
	   *input_string* - operation to be preformed on remote machinge
	   *my_key*	   - location of the key
	   *user*		 - the amazon user (usually ubuntu or root)
	"""
	res = 0
	if not silent:
		print('{message} for {node}'.format(message = message, node = node['name']))
		sys.stdout.flush()

	os_res = _remote(host = node['public_dns'], cmd = input_string,
					credential = my_key, test = False, user = user,silent = True)
	if os_res != 0:
		print('{node} failed:'.format(node = node['name']))
		if not silent:
			_remote(host = node['public_dns'], cmd = input_string,
					credential = my_key, test = True, user = user,silent = False)
		sys.stdout.flush()
		res = 1
	elif not silent:
		print('{node} is done'.format(node = node['name']))
		sys.stdout.flush()  
	
	return(res)
		
def update_apt_get_to_nodes(nodes, my_key, user = 'ubuntu', silent= False, processes = None):
	""" Running the update on all system
		*nodes*	     - list from get_dns_names or single element from the same
		*user*	     - the amazon user (usually ubuntu or root)
		*my_key*     - location of the key
		*proccesses* - number of processes
	"""
	
	if not isinstance(nodes,list):
		nodes = [nodes]
		

	input_ = [(node, silent, my_key, user) for node in nodes]
	
	pool = multiprocessing.Pool(processes = processes)
	res = pool.map(_update_apt_get_to_nodes_loop, input_)


	pool.close()
	pool.join()
	
	return sum(res)

def _update_apt_get_to_nodes_loop(args):
	'''
		writting the loop in update_apt_get_to_nodes
		in a format suitable to multiprocesses
	'''
	
	#args[0] is node
	node   = args[0]
	silent = args[1]
	my_key = args[2]
	user   = args[3]
	
	input_string = 'sudo apt-get -y --force-yes update'
	res_update   = _remote_on_node(node, silent, my_key, input_string, user, message = 'update apt-get')	
	
	input_string = 'sudo apt-get -y --force-yes upgrade -y'
	res_upgrade  = _remote_on_node(node, silent, my_key, input_string, user, message = 'upgrade apt-get') 	  
	
	return(res_update + res_upgrade)


def copy_file_from_node(node, file_location, destination, my_key, user = 'ubuntu', silent = False):
	"""
		copies the file from the node to destination of the local computer (using scp)
		*file_location* - either a string or a list of location of files
		*destination*   - desitnation of the fiels
		*nodes*		 - list from get_dns_names or single element from the same
		*my_key*		- location of the key
		*user*		  - the amazon user (usually ubuntu or root)	
	"""


	if isinstance(file_location, list):
		file_location = " ".join(file_location)
	
	if not silent:
		print('copying {files} to local computer {dest}'.format(files= file_location, dest = destination))
	
	
	if not silent:
		print('copying files to {name}'.format(name = node['name']), end = '')
		sys.stdout.flush()
	
	file_location += ' ' + destination
	destination = file_location
	os_res = _remote(host = node['public_dns'], src = '',
				dest=destination ,credential = my_key, test = False, user = user, silent = True)
	
	if os_res != 0:
		print(' failed : ')
		if not silent:
			_remote(host = node['public_dns'], src = '',
				dest=destination ,credential = my_key, test = False, user = user, silent = False)
		sys.stdout.flush()
		return os_res
		
	elif not silent:
		print(' done')
		sys.stdout.flush() 

	return os_res

def copy_file_to_nodes(nodes, file_location, destination, my_key, user = 'ubuntu', silent = False):
	"""
		copies the files in file_location to destination of the nodes (using scp)
		*file_location* - either a string or a list of location of files
		*destination*   - desitnation of the fiels
		*nodes*		 - list from get_dns_names or single element from the same
		*my_key*		- location of the key
		*user*		  - the amazon user (usually ubuntu or root)
	"""
	
	if not isinstance(nodes,list):
		nodes = [nodes]	
	
	if isinstance(file_location, list):
		file_location = " ".join(file_location)
	
	
	if not silent:
		print('copying {files} to external {dest}'.format(files= file_location, dest = destination))
	
	os_res = 0	
	for node in nodes:
		
		if not silent:
			print('copying files to {name}'.format(name = node['name']), end = '')
			sys.stdout.flush()
			
		os_res = _remote(host = node['public_dns'], src = file_location,
					dest=destination ,credential = my_key, test = False, user = user, silent = True)
		
		if os_res != 0:
			print(' failed : ')
			if not silent:
				_remote(host = node['public_dns'], src = file_location,
						dest=destination ,credential = my_key, test = True, user = user, silent = False)
			sys.stdout.flush()
			return os_res
			
		elif not silent:
			print(' done')
			sys.stdout.flush() 
	
	return os_res

def create_file_to_nodes(nodes, file_name, my_key, file_content ='', sudo = False, user = 'ubuntu', silent = False,
						 test = False):
	"""
		creates an empty file  to destination of the nodes (using scp)
		*file_name*	 - file of the to be created
		*file_content*  - content of the file (will be append to file name)
		*nodes*		 - list from get_dns_names or single element from the same
		*my_key*		- location of the key
		*user*		  - the amazon user (usually ubuntu or root)
		*sudo*		  - use sudo?
	"""
	
	if not isinstance(nodes,list):
		nodes = [nodes]	
	
	if sudo == False:
		sudo = ''
	else:
		sudo = 'sudo '
	
	
	string_dict = {'key'	   : my_key,
				   'user'	  : user,
				   'hostname'  : None,
				   'sudo'	  : sudo,
				   'file_name' : file_name,
				   'file_content' : file_content
				  }
		
	for node in nodes:
		
		if not silent:
			print("appending to {file_name} in {node}".format(file_name = file_name,
															  node = node['name']),
				  end = '')
			sys.stdout.flush()
			
		string_dict['hostname'] = node['public_dns']
		input_string = "ssh -i {key} -o 'StrictHostKeyChecking no'  {user}@{hostname} '{sudo}touch {file_name}'".format(
						**string_dict)
		
		if not test:
			os_res = os.system(input_string)
		else:
			print( '\n'+ input_string)
			os_res = 0
			
		if os_res != 0:
			print("touch file for {node} failed".format(node = node['name']))
			break
		
		
		if len(file_content) > 0:
			input_string1 = "echo  '{file_content}'|".format(**string_dict)
			input_string2 = "ssh -i {key} -o 'StrictHostKeyChecking no' ubuntu@{hostname}".format(
							   **string_dict)
			input_string3 = " '{sudo}tee --append {file_name}'".format(
							   **string_dict)
			
			input_string =input_string1 + input_string2 + input_string3
			if not test:
				os_res = os.system(input_string)
			else:
				print(input_string)
				os_res = 0
		
		
		
		if os_res != 0:
			print("file_append for {node} failed".format(node = node['name']))
			break
		
		if not silent:
			print(" done")
			sys.stdout.flush()			
	
def import_package_to_nodes(packages, nodes, my_key, method = 'apt', user = 'ubuntu', silent = False, processes = None):
	""" import the packages to all nodes
		*packages*		  - either list or string contaning the package to be installed
		*method*			- either pip or apt
		*nodes*			 - list from get_dns_names or single element from the same
		*my_key*			- location of the key
		*user*			  - the amazon user (usually ubuntu or root)
	  *processes*		 - number of processes to use
	"""
	
	
	
	if not isinstance(nodes,list):
		nodes = [nodes]
	
	if isinstance(packages, list):
		packages = " ".join(packages)
	
	if method == 'apt':
		method = 'apt-get -y --force-yes install'
	if method == 'pip':
		method = 'pip install'
		
	input_string = 'sudo {method} {packages}'.format(method = method, packages = packages)
	
	if not silent:
		print( 'installing the packages : {packages}\n'.format(packages = packages))
		sys.stdout.flush()
	
	
	
	pool = multiprocessing.Pool(processes = processes)
	input_ = [(node, silent, my_key, input_string, user, 'installing package') for node in nodes]
	res = pool.map(_remote_on_node_wrapper, input_)


	pool.close()
	pool.join()
	
	return sum(res)
	