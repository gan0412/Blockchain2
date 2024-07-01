import hashlib
import json
from textwrap import dedent
import logging
from time import time
from uuid import uuid4
from waitress import serve
from flask import Flask, jsonify, request, render_template
from urllib.parse import urlparse

#program simulates a basic blockchain that can recieve transactions and perform proof of work
class Blockchain(object):
    def __init__(self):
        self.current_transactions = [] #all the transactions for the current block
        self.chain = [] #where all blocks are stored
        self.nodes = set() #where the nodes or users are stored

        # Create the genesis block
        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """
        Create a new Block in the Blockchain
        :param proof: <int> The proof given by the Proof of Work algorithm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }
        """every block must always point to its previous block's hash 
        (except genesis block)"""
        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block) #adds newly created block to the chain
        return block #returns newly created block

    def new_transaction(self, sender, recipient, amount):
        """
        Creates a new transaction to go into the next mined Block
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <int> Amount
        :return: <int> The index of the Block that will hold this transaction
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        return self.last_block['index'] + 1 #index of block to hold transaction

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """proof of work presents a computational challenge to solve before any new
        block is added. This helps to ensure that malicious actors cannot easily modify the blockchain"""

        """
        Simple Proof of Work Algorithm:
         - Find a number p' such that hash(pp') contains leading 4 zeroes, where p is the previous p'
         - p is the previous proof, and p' is the new proof
        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1 #keeps incrementing proof by 1 until valid proof is found

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?
        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not.
        """

        guess = f'{last_proof}{proof}'.encode() #concatenates last proof and current proof, encodes it into bytes
        guess_hash = hashlib.sha256(guess).hexdigest() #calculates hash of the guess and converts into a hexadecimal string
        return guess_hash[:4] == "0000" #checks if the first four characters are zero, if so proof is a valid proof

    @staticmethod
    def hash(block):
        """
        this method is useful to detect any modifications or tampering to blocks since even a slight
        change to one of the properties changes the hash. Hashes are also different to identify different blocks
        and point to previous blocks
        """

        """
        Creates a SHA-256 hash of a Block
        :param block: <dict> Block
        :return: <str>
        """

        # We must make sure that the Dictionary is Ordered, or we'll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode() #converts block into a json string
        #using dumps method, ensures dictionary is sorted and encodes it into bytes
        return hashlib.sha256(block_string).hexdigest() #calculates hash of block_string and converts to hexadecimal

    def valid_chain(self, chain):
        """
        Determine if a given blockchain is valid
        :param chain: <list> A blockchain
        :return: <bool> True if valid, False if not
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Check that the hash of the block is correct
            if block['previous_hash'] != self.hash(last_block): #checks if the current block points to previous block hash
                return False

            # Check that the Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']): #checks that the proofs are valid
                return False

            last_block = block
            current_index += 1

        return True
    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg. 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address) #converts address to url object to allow access to different url components
        self.nodes.add(parsed_url.netloc) #hostname and port number are included in netloc to give location

    def resolve_conflicts(self):
        """
        This is our Consensus Algorithm, it resolves conflicts
        by replacing our chain with the longest one in the network.
        :return: <bool> True if our chain was replaced, False if not. It does this by looping through each chain
        that a node stores. If a neighbor has a valid chain that is greater than the node's chain, it replaces the
        node's chain
        """

        neighbours = self.nodes
        new_chain = None

        # We're only looking for chains longer than ours
        max_length = len(self.chain)

        # Grab and verify the chains from all the nodes in our network
        for node in neighbours: #traverse through each node in neighbors
            response = request.get(f'http://{node}/chain') #get request to execute the full_chain method

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discovered a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False


# logging.basicConfig(level=logging.INFO)
#
# # Instantiate our Node
# app = Flask(__name__)
#
# # Generate a globally unique address for this node
# node_identifier = str(uuid4()).replace('-', '')
#
# # Instantiate the Blockchain
# blockchain = Blockchain()
#
# @app.route('/', methods=['GET'])
# def index():
#     """Homepage: all buttons are viewable and clickable"""
#     return render_template('index.html', chain=blockchain.chain)
#
# @app.route('/transactions/new', methods=['GET', 'POST'])
# def new_transaction():
#     """Handle transaction form submission and display."""
#     if request.method == 'POST':
#         values = request.form  # Get data from the form
#
#         # Check that the required fields are in the POST'ed data
#         required = ['sender', 'recipient', 'amount']
#         if not values or not all(k in values for k in required):
#             return 'Missing values', 400
#
#         # Create a new Transaction
#         index = blockchain.new_transaction(values['sender'], values['recipient'], int(values['amount']))
#         message = f'Transaction will be added to Block {index}'
#         return render_template('index.html', chain=blockchain.chain, message=message)
#
#     return render_template('new_transaction.html')
#
# @app.route('/mine', methods=['GET'])
# def mine():
#     # We run the proof of work algorithm to get the next proof...
#     last_block = blockchain.last_block
#     last_proof = last_block['proof']
#     proof = blockchain.proof_of_work(last_proof)
#
#     # We must receive a reward for finding the proof.
#     # The sender is "0" to signify that this node has mined a new coin.
#     blockchain.new_transaction(
#         sender="0",
#         recipient=node_identifier,
#         amount=1,
#     )
#
#     # Forge the new Block by adding it to the chain
#     previous_hash = blockchain.hash(last_block)
#     block = blockchain.new_block(proof, previous_hash)
#
#     response = {
#         'message': "New Block Forged",
#         'index': block['index'],
#         'transactions': block['transactions'],
#         'proof': block['proof'],
#         'previous_hash': block['previous_hash'],
#     }
#     return render_template('mine.html', block=block)
#
#     #return jsonify(response), 200
#
#
# @app.route('/chain', methods=['GET'])
# def full_chain():
#     response = {
#         'chain': blockchain.chain,
#         'length': len(blockchain.chain),
#     }
#     return render_template('chain.html', chain=response['chain'])
#
# @app.route('/nodes/register', methods=['GET', 'POST'])
# def register_nodes():
#     if request.method == 'POST':
#         nodes = request.form.get('nodes')
#         if nodes is None:
#             return "Error: Please supply a valid list of nodes", 400
#
#         nodes = nodes.split(',')  # Assuming nodes are comma-separated in the form
#         for node in nodes:
#             node = node.strip() # Remove leading/trailing whitespace
#             blockchain.register_node(node)
#
#         response = {
#             'message': 'New nodes have been added',
#             'total_nodes': list(blockchain.nodes),
#         }
#         return render_template('register_node.html', message=response['message'])
#
#     return render_template('register_node.html')
#
#
# #resolves conflicts and updates valid and longest chain to all nodes
# @app.route('/nodes/resolve', methods=['GET'])
# def consensus():
#     replaced = blockchain.resolve_conflicts()
#
#     if replaced:
#         response = {
#             'message': 'Our chain was replaced',
#             'new_chain': blockchain.chain
#         }
#     else:
#         response = {
#             'message': 'Our chain is authoritative',
#             'chain': blockchain.chain
#         }
#
#     return render_template('resolve_conflicts.html', message=response['message'])
#
# if __name__ == '__main__':
#     #host 0.0.0.0 ensures flask server listens to all available network interfaces, using 127.0.0.1 will only allow
#     #my machine to access app
#     serve(app, host="127.0.0.1", port=5000) #127.0.0.1 allows deployed server to only be accessed from local server
#     # app.run(host='0.0.0.0', port=5000) #0.0.0.0 allows any machine to access server and send requests