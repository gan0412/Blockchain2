from flask import Flask, jsonify, request, render_template
from uuid import uuid4
import Blockchain
import logging



logging.basicConfig(level=logging.INFO)

# Instantiate our Node
app = Flask(__name__)

# Generate a globally unique address for this node
node_identifier = str(uuid4()).replace('-', '')

# Instantiate the Blockchain
blockchain = Blockchain.Blockchain()

@app.route('/', methods=['GET'])
def index():
    """Homepage: all buttons are viewable and clickable"""
    return render_template('index.html', chain=blockchain.chain)

@app.route('/transactions/new', methods=['GET', 'POST'])
def new_transaction():
    """Handle transaction form submission and display."""
    if request.method == 'POST':
        values = request.form  # Get data from the form

        # Check that the required fields are in the POST'ed data
        required = ['sender', 'recipient', 'amount']
        if not values or not all(k in values for k in required):
            return 'Missing values', 400

        # Create a new Transaction
        index = blockchain.new_transaction(values['sender'], values['recipient'], int(values['amount']))
        message = f'Transaction will be added to Block {index}'
        return render_template('index.html', chain=blockchain.chain, message=message)

    return render_template('new_transaction.html')

@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get the next proof...
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin.
    blockchain.new_transaction(
        sender="0",
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }
    return render_template('mine.html', block=block)

    #return jsonify(response), 200


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return render_template('chain.html', chain=response['chain'])

@app.route('/nodes/register', methods=['GET', 'POST'])
def register_nodes():
    if request.method == 'POST':
        nodes = request.form.get('nodes')
        if nodes is None:
            return "Error: Please supply a valid list of nodes", 400

        nodes = nodes.split(',')  # Assuming nodes are comma-separated in the form
        for node in nodes:
            node = node.strip() # Remove leading/trailing whitespace
            blockchain.register_node(node)

        response = {
            'message': 'New nodes have been added',
            'total_nodes': list(blockchain.nodes),
        }
        return render_template('register_node.html', message=response['message'])

    return render_template('register_node.html')


#resolves conflicts and updates valid and longest chain to all nodes
@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain': blockchain.chain
        }

    return render_template('resolve_conflicts.html', message=response['message'])

