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
CSV_SAVE_FOLDER = 'D:\\VirtualStudio_Code_Programming\\python_dash_plotly\\mmWave_webServer\\data_frame_sta_csv'

FORMAT = '%(asctime)s %(levelname)s: %(message)s'
g_is_detected_exit = False
g_last_file_data = [ pd.DataFrame(), pd.DataFrame() ]
g_last_file_path = ''

logging.basicConfig( level=logging.INFO, format=FORMAT, stream=sys.stdout )

P_FILE_PATH = 'C:\\Users\\USER\\Downloads\\pmb\\20200902\\Data'

FILE_NAMES = [ name.split( '\\' )[ -1 ] for name in glob.glob( os.path.join( P_FILE_PATH, '*.json' ) ) ]


def get_data( path: str ) -> pd.DataFrame():
    global g_last_file_data, g_last_file_path

    if g_last_file_path != path:
        try:
            with open( file=path, mode='r' ) as f:
                file_df = pd.DataFrame( json.load( fp=f ) ).T
                file_df = file_df.set_index( pd.Index( range( file_df.count()[ 0 ] ) ) )
            s_data_df = pd.DataFrame(
                sum( [ v6 for v6 in file_df.loc[ :, 'v6' ] ], [] ),
                index=[
                    sum( [ [ int( index ) - 1 ] * len( v6 ) for index, v6 in file_df.loc[ :, 'v6' ].items() ], [] ),
                    sum( [ list( range( len( v6 ) ) ) for v6 in file_df.loc[ :, 'v6' ] ], [] )
                ],
                columns=[ 'radius', 'angle', 'doppler', 'snr' ] )
            s_data_df = s_data_df.assign(
                pos_x=lambda x: x.radius * np.sin( x.angle ), pos_y=lambda x: x.radius * np.cos( x.angle ), cluster=-1 )

            g_last_file_data[ 0 ] = s_data_df

            #static
            snr_stc, dop_stc, nodata = [], [], pd.Series(
                {
                    'count': 0,
                    'max': 0,
                    'min': 0,
                    'mean': 0,
                    'std': 0,
                    '50%': 0,
                    '25%': 0,
                    '75%': 0,
                }, name='nodata' )
            for x in range( file_df.count()[ 0 ] ):
                try:
                    snr_stc.append( s_data_df.loc[ x, 'snr' ].describe() )
                    dop_stc.append( s_data_df.loc[ x, 'doppler' ].describe() )
                except KeyError:
                    snr_stc.append( nodata )
                    dop_stc.append( nodata )
            snr_stc_df = pd.DataFrame( data=snr_stc, index=range( file_df.count()[ 0 ] ) )
            dop_stc_df = pd.DataFrame( data=dop_stc, index=range( file_df.count()[ 0 ] ) )
            frame_base_df = pd.DataFrame( file_df.loc[ :, 'time' ] )
            try:
                frame_base_df = frame_base_df.assign(
                    mCf='none',
                    bCf=0,
                    count=list( snr_stc_df.loc[ :, 'count' ] ),
                    snrMax=list( snr_stc_df.loc[ :, 'max' ] ),
                    snrMin=list( snr_stc_df.loc[ :, 'min' ] ),
                    snrMean=list( snr_stc_df.loc[ :, 'mean' ] ),
                    snrStd=list( snr_stc_df.loc[ :, 'std' ] ),
                    snrHalf=list( snr_stc_df.loc[ :, '50%' ] ),
                    dopMax=list( dop_stc_df.loc[ :, 'max' ] ),
                    dopMin=list( dop_stc_df.loc[ :, 'min' ] ),
                    dopMean=list( dop_stc_df.loc[ :, 'mean' ] ),
                    dopStd=list( dop_stc_df.loc[ :, 'std' ] ),
                    dopHalf=list( dop_stc_df.loc[ :, '50%' ] ),
                )
            except ValueError as e:
                print( file_df )
                print( frame_base_df )
                print( file_df.count()[ 0 ] )
                print( e )
            #print( frame_base_df )
            g_last_file_data[ 1 ] = frame_base_df
            g_last_file_path = path
        except FileNotFoundError as e:
            print( e )
        '''except TypeError as e:
            print( e )'''
    return g_last_file_data[ 0 ]


controls = dbc.Card(
    [
        dbc.FormGroup(
            [
                dbc.Label( "file choice" ),
                dcc.Dropdown(
                    id="file-name",
                    options=[ {
                        "label": file_name,
                        "value": file_name
                    } for file_name in FILE_NAMES ],
                    value=FILE_NAMES[ 0 ],
                ),
                dbc.Label( "data count" ),
                dbc.Input( id="data-count", type="number", value=0 ),
                dbc.Label( "clusterer type" ),
                dcc.Dropdown(
                    id="clusterer-type",
                    options=[
                        {
                            "label": cluster_method,
                            "value": cluster_method
                        } for cluster_method in [ 'snr', 'kMean+s', 'mine', 'other' ]
                    ],
                    value='snr',
                ),
            ] ),
        dbc.FormGroup(
            [
                dbc.Label( "tag target" ),
                dcc.Dropdown(
                    id="tag-target",
                    options=[ {
                        "label": tag_target,
                        "value": tag_target
                    } for tag_target in [ 'none', 'frame', 'cluster' ] ],
                    value='none',
                ),
                dbc.Label( "tag value" ),
                html.Br(),
                dbc.ButtonGroup(
                    [ dbc.Button( 'none' ) ],
                    size="md",
                    className="mr-1",
                    id='tag-value',
                ),
                html.Br(),
                dbc.Button( 'save to csv', color="danger", disabled=True, id='save-2-csv' ),
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

    graph_df = pd.DataFrame(
        [
            [
                is_closer( data_df.loc[ m, [ 'pos_x', 'pos_y' ] ], data_df.loc[ n, [ 'pos_x', 'pos_y' ] ], 0.3 )
                for m in set( data_df.index )
            ] for n in set( data_df.index )
        ] )

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
            html.H1( "data manager sys" ),
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col( [
                        dbc.Row( controls ),
                        dbc.Row(
                            html.H4( "", id='tag-give-back' ),
                            justify="center",
                        ),
                    ], md=4 ),
                    dbc.Col( dcc.Graph( id="cluster-graph" ), md=8 )
                ],
                align="center",
            ),
        ],
        fluid=True,
    )


server = Flask( __name__ )
tag_maker = dash.Dash(
    __name__,
    server=server,
    url_base_pathname='/tag/',
    external_stylesheets=[ dbc.themes.BOOTSTRAP ],
    suppress_callback_exceptions=True )

tag_maker.layout = make_layout_RTchart()
'''
@tag_maker.callback(
    [
        Output( "data-count", "value" ),
        Output( "file-name", "value" ),
    ],
    Input( "tag-give-back", "children" ),
)
def except_data_count( gb: str ):
    if 'x01' in gb:
        return 0, gb.split( 'x01' )[ -1 ]
    elif 'x02' in gb:
        return 0, gb.split( 'x02' )[ -1 ]
    elif 'x03' in gb:
        return int( gb.split( 'x03' )[ -2 ] ), gb.split( 'x03' )[ -1 ]'''


@tag_maker.callback( Output( "tag-value", "children" ), [ Input( "tag-target", "value" ) ] )
def filter_options( v ):
    """option belong option v"""
    btn_n = [ 'none', 'noise', 'reflect', 'walker', 'moto', 'car' ]
    btn_c = { 'none': "secondary", 'noise': "warning", 'reflect': "warning", 'walker': "info", 'moto': "info", 'car': "info" }
    btn_a = {
        'none': [ ( True, n, btn_c[ n ] ) for n in btn_n ],
        'frame': ( f := [ ( False, n, btn_c[ n ] ) for n in btn_n ] ),
        'cluster': f
    }

    return [ dbc.Button( btn[ 1 ], color=btn[ 2 ], disabled=btn[ 0 ], id=f"tag-v-{btn[1]}" ) for btn in btn_a[ v ] ]


@tag_maker.callback(
    [
        Output( "tag-give-back", "children" ),
        Output( 'save-2-csv', 'disabled' ),
        Output( "data-count", "value" ),
    ],
    [ Input( f"tag-v-{btn}", "n_clicks" ) for btn in [ 'none', 'noise', 'reflect', 'walker', 'moto', 'car' ] ],
    [
        State( "file-name", "value" ),
        State( "data-count", "value" ),
        State( "tag-target", "value" ),
    ],
)
def on_button_click( n1, n2, n3, n4, n5, n6, fileName, dataCount, tagTarget ):
    global g_last_file_data

    tag_d = { 'none': 0, 'noise': 0, 'reflect': 0, 'walker': 1, 'moto': 1, 'car': 1 }

    ctx = dash.callback_context

    if not ctx.triggered or tagTarget == 'none':
        return "", True, dataCount
    else:
        button_id = ctx.triggered[ 0 ][ "prop_id" ].split( "." )[ 0 ]

    tag = button_id.split( '-' )[ -1 ]

    g_last_file_data[ 1 ].at[ dataCount, 'mCf' ] = tag
    g_last_file_data[ 1 ].at[ dataCount, 'bCf' ] = tag_d[ tag ]

    if dataCount == g_last_file_data[ 1 ].count()[ 0 ] - 1:
        save_btn = False
    else:
        save_btn = True

    #print( g_last_file_data[ 1 ] )
    if not save_btn:
        #print( 'ininin' )
        global CSV_SAVE_FOLDER

        try:
            g_last_file_data[ 1 ].to_csv( path_or_buf=os.path.join( CSV_SAVE_FOLDER, fileName.split( '.' )[ 0 ] + '.csv' ) )
        except FileNotFoundError as e:
            return str( e ), True, dataCount
            raise e
        except TypeError as e:
            return str( e ), True, dataCount
            raise e
        return f"file : {''.join( fileName.split( '.' )[ 0 ], '.csv' )} saved !!", False, dataCount + 1000

    return f"{fileName}[{dataCount}] is {tag}", save_btn, dataCount + 1


@tag_maker.callback(
    #[
    Output( "cluster-graph", "figure" ),
    #Output( "tag-give-back", "children" ),
    #Output( "data-count", "value" ),
    #Output( "file-name", "value" ),
    #],
    [
        Input( "file-name", "value" ),
        Input( "data-count", "value" ),
        Input( "clusterer-type", "value" ),
    ],
)
def make_graph( fileName, dataCount, clustererType ):
    # minimal input validation, make sure there's at least one cluster
    global FILE_NAMES

    file_v6_df = get_data( os.path.join( P_FILE_PATH, fileName ) )

    try:
        data_df = file_v6_df.loc[ dataCount ]
    except KeyError:
        if dataCount < 0:
            return go.Figure()  #, 'data count should >= 0'  #, 0, fileName
        elif dataCount > file_v6_df.iloc[ -1 ].name[ 0 ]:
            try:
                return go.Figure()  #, 'no more data in this file'  #, 0, FILE_NAMES[ FILE_NAMES.index( value=fileName ) + 1 ]
            except IndexError as e:
                raise e
        else:
            return go.Figure()  #, 'this frame have no data'  #, dataCount + 1, fileName
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
        t1 = dt.datetime.now()
        cluster_ana( data_df=data_df )
        print( dt.datetime.now() - t1 )
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
        f"it's {fileName}['{min( dataCount, file_v6_df.iloc[ -1 ].name[ 0 ] - 1)}'] \n {g_last_file_data[1].loc[dataCount,'time']}",
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
        'shapes': [
            {
                'type': path[ 4 ],
                'x0': path[ 0 ],
                'x1': path[ 2 ],
                'y0': path[ 1 ],
                'y1': path[ 3 ],
                'name': 'vaild range'
            } for path in
            [ [ 0, 0, -3 * math.sqrt( 3 ), 3, 'line' ], [ 0, 0, 3 * math.sqrt( 3 ), 3, 'line' ], [ -6, -6, 6, 6, 'circle' ] ]
        ],
    }

    return go.Figure( data=data, layout=layout )  #, dataCount, fileName


@server.route( '/', methods=[ 'GET' ] )
def hello_world():
    return 'Hello World!'


server.run( host='0.0.0.0', port=2233 )  #=random.randint( 2000, 9000 ) )
