import json
from threading import Thread
import random
from flask import Flask, request
import datetime as dt
import glob
import logging
import numpy as np
import dash
import flask
import dash_bootstrap_components as dbc
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import sys
import os
import math
from scipy.spatial import ConvexHull, qhull
import pandas as pd

NO_SAVE = True

FORMAT = '%(asctime)s %(levelname)s: %(message)s'
g_is_detected_exit = False
g_last_file_data = pd.DataFrame()
g_last_file_path = ''

logging.basicConfig( level=logging.INFO, format=FORMAT, stream=sys.stdout )

P_FILE_PATH = 'C:\\Users\\USER\\Downloads\\pmb\\20200902\\Data'

FILE_NAMES = [ name.split( '\\' )[ -1 ] for name in glob.glob( os.path.join( P_FILE_PATH, '*.json' ) ) ]


def get_data( path: str ) -> dict:
    global g_last_file_data, g_last_file_path

    if g_last_file_path == path:
        return g_last_file_data
    try:
        with open( file=path, mode='r' ) as f:
            return json.load( fp=f )
    except FileNotFoundError as e:
        print( e )
        return { 'error': e }
    except TypeError as e:
        print( e )
        return { 'error': e }


controls = dbc.Card(
    [
        dbc.FormGroup( [
            dbc.Label( "file choice" ),
            dcc.Dropdown(
                id="file-name",
                options=[ {
                    "label": file_name,
                    "value": file_name
                } for file_name in FILE_NAMES ],
                value=FILE_NAMES[ 0 ],
            ),
        ] ),
        dbc.FormGroup( [
            dbc.Label( "data count" ),
            dbc.Input( id="data-count", type="number", value=0 ),
        ] ),
        dbc.FormGroup( [
            dbc.Label( "clusterer type" ),
            dcc.Dropdown(
                id="clusterer-type",
                options=[ {
                    "label": file_name,
                    "value": file_name
                } for file_name in [ 'snr', 'kMean+s', 'mine', 'other' ] ],
                value='snr',
            ),
        ] ),
    ],
    body=True,
)


class ReadDataMag():
    """"""

    def __init__( self, initPath: str, initCount: int ):
        self.path = initPath
        self.count = initCount

        self.file_data = {} if 'error' in ( data := get_data( self.path ) ).keys() else data


def cluster_ana( data_df: pd.DataFrame() ) -> pd.DataFrame():

    def is_closer( point0: list, point1: list, dist: float ) -> bool:
        return np.sqrt( abs( point0[ 0 ] - point1[ 0 ] )**2 + abs( point0[ 1 ] - point1[ 1 ] )**2 ) < dist

    def mark_recursion( index: int, graphDf: pd.DataFrame(), dataDf: pd.DataFrame(), cluster: int ) -> None:
        if sum( graphDf.iloc[ index ] ) == 0:
            if dataDf.at[ index, 'cluster' ] == -1:
                dataDf.at[ index, 'cluster' ] = cluster
            return
        else:
            for inner_index, is_closer in graphDf.iloc[ index ].items():
                if is_closer:
                    graphDf.iat[ index, inner_index ] = False
                    graphDf.iat[ inner_index, index ] = False
                    dataDf.at[ inner_index, 'cluster' ] = cluster
                    mark_recursion( inner_index, graphDf, dataDf, cluster )

    graph_df = pd.DataFrame( [ [
        is_closer( data_df.loc[ m, [ 'pos_x', 'pos_y' ] ], data_df.loc[ n, [ 'pos_x', 'pos_y' ] ], 0.3 )
        for m in set( data_df.index )
    ] for n in set( data_df.index ) ] )

    cluster = 0
    for index, value in data_df.cluster.items():
        if value != -1:
            continue
        mark_recursion( index=index, graphDf=graph_df, dataDf=data_df, cluster=cluster )
        cluster += 1

    return data_df


def make_layout_RTchart():
    """製作一個固定的附帶選擇的圖形"""
    return dbc.Container(
        [
            html.H1( "Iris k-means clustering" ),
            html.Hr(),
            dbc.Row(
                [ dbc.Col( controls, md=4 ), dbc.Col( dcc.Graph( id="cluster-graph" ), md=8 ) ],
                align="center",
            ),
        ],
        fluid=True,
    )


server = Flask( __name__ )
tag_maker = dash.Dash( __name__,
                       server=server,
                       url_base_pathname='/tag/',
                       external_stylesheets=[ dbc.themes.BOOTSTRAP ],
                       suppress_callback_exceptions=True )

tag_maker.layout = make_layout_RTchart()


@tag_maker.callback(
    Output( "cluster-graph", "figure" ),
    [
        Input( "file-name", "value" ),
        Input( "data-count", "value" ),
        Input( "clusterer-type", "value" ),
    ],
)
def make_graph( fileName, dataCount, clustererType ):
    # minimal input validation, make sure there's at least one cluster
    file_data = get_data( os.path.join( P_FILE_PATH, fileName ) )

    data_df = pd.DataFrame( file_data[ str( min( max( 0, dataCount ),
                                                 len( file_data ) - 1 ) ) ][ 'v6' ],
                            columns=[ 'radius', 'angle', 'doppler', 'snr' ] )
    data_df = data_df.assign( pos_x=lambda x: x.radius * np.sin( x.angle ),
                              pos_y=lambda x: x.radius * np.cos( x.angle ),
                              cluster=-1 )
    data_df = data_df.sort_values( by='snr', ascending=False )

    #print( data_df )

    if clustererType == 'snr':
        data = [
            go.Scatter(
                x=data_df[ 'pos_x' ],
                y=data_df[ 'pos_y' ],
                mode="markers",
                marker={
                    "size": data_df[ 'snr' ],
                    'sizemode': 'area'
                },  #[ math.log10( point[ 3 ] ) for point in frame_data[ "v6" ] ] },
                name="raw & size in snr",
            ),
        ]
    else:
        cluster_ana( data_df=data_df )
        data = [
            go.Scatter(
                x=data_df.loc[ data_df.cluster == c, 'pos_x' ],
                y=data_df.loc[ data_df.cluster == c, 'pos_y' ],
                text=data_df.index[ data_df.cluster == c ].tolist(),
                mode="markers",
                marker={
                    "size": data_df.loc[ data_df.cluster == c, 'snr' ],
                    'sizemode': 'area'
                },  #[ math.log10( point[ 3 ] ) for point in frame_data[ "v6" ] ] },
                name=f"cluster-{c} (size in snr)",
            ) for c in set( data_df.cluster )
        ]

    layout = {
        'title':
        f"it's {fileName}['{min( dataCount, len( file_data ) - 1 )}'] \n {file_data[ str(dataCount) ]['time']}",
        "xaxis": {
            "title": 'x(m)',
            'range': [ -4, 4 ],
        },
        "yaxis": {
            "title": 'y(m)',
            'range': [ -1, 7 ],
            'scaleanchor': 'x',
            'scaleratio': 1
        },
        'height':
        700,
        'shapes': [ {
            'type': path[ 4 ],
            'x0': path[ 0 ],
            'x1': path[ 2 ],
            'y0': path[ 1 ],
            'y1': path[ 3 ],
            'name': 'vaild range'
        } for path in [ [ 0, 0, -3 * math.sqrt( 3 ), 3, 'line' ], [ 0, 0, 3 *
                                                                    math.sqrt( 3 ), 3, 'line' ], [ -6, -6, 6, 6, 'circle' ] ] ],
    }

    return go.Figure( data=data, layout=layout )


@server.route( '/', methods=[ 'GET' ] )
def hello_world():
    return 'Hello World!'


server.run( host='0.0.0.0', port=2233 )  #=random.randint( 2000, 9000 ) )
