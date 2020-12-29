#%%

import queue

#%%


class HuffmanNode( object ):

    def __init__( self, left=None, right=None, root=None ):
        self.left = left
        self.right = right

    def children( self ):
        return ( ( self.left, self.right ) )


#%%

freq = [
    ( 1.167, 'a' ), ( 1.492, 'b' ), ( 1.782, 'c' ), ( 4.253, 'd' ), ( 52.702, 'e' ), ( 1.228, 'f' ), ( 1.015, 'g' ),
    ( 1.094, 'h' ), ( 1.966, 'i' ), ( 0.153, 'j' ), ( 0.747, 'k' ), ( 4.025, 'l' ), ( 1.406, 'm' ), ( 1.749, 'n' ),
    ( 1.507, 'o' ), ( 1.929, 'p' ), ( 0.095, 'q' ), ( 5.987, 'r' ), ( 6.327, 's' ), ( 1.056, 't' ), ( 2.758, 'u' ),
    ( 1.037, 'v' ), ( 2.365, 'w' ), ( 0.150, 'x' ), ( 1.974, 'y' ), ( 0.074, 'z' )
]
#%%


def create_tree( frequencies ):
    p = queue.PriorityQueue()
    for value in frequencies:  # 1. Create a leaf node for each symbol
        p.put( value )  #    and add it to the priority queue
    while p.qsize() > 1:  # 2. While there is more than one node
        l, r = p.get(), p.get()  # 2a. remove two highest nodes
        node = HuffmanNode( l, r )  # 2b. create internal node with children
        p.put( ( l[ 0 ] + r[ 0 ], node ) )  # 2c. add new node to queue
    return p.get()  # 3. tree is complete - return root node


node = create_tree( freq )

#%%


def walk_tree( node, prefix="", code={} ):
    """
    node => tuple(freq, HuffmanNode|character)
    """
    if isinstance( node[ 1 ], HuffmanNode ):  # node[1] is HuffmanNode
        code1 = walk_tree( node[ 1 ].left, '0', code.copy() )  # error when not copy
        code2 = walk_tree( node[ 1 ].right, '1', code.copy() )
        if len( code1 ) > 0:
            for k, v in code1.items():
                code[ k ] = prefix + v
        if len( code2 ) > 0:
            for k, v in code2.items():
                code[ k ] = prefix + v
    else:  # node[1]
        code[ node[ 1 ] ] = prefix
    return ( code )


code = walk_tree( node )
#%%

# op
for i in sorted( freq, reverse=True ):
    try:
        print( i[ 1 ], '{:6.2f}'.format( i[ 0 ] ), code[ i[ 1 ] ] )
    except Exception as e:
        print( e )
        continue
#%%
