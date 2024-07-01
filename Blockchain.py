import hashlib
import json
from textwrap import dedent
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

