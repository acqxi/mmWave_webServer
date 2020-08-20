import json
from threading import Thread
import random
from flask import Flask, request
from dash import Dash
import dash_html_components as html

flaskServer = Flask( __name__ )
dashChartApp = Dash( __name__, server=flaskServer, url_base_pathname='/dashChart' )
dashChartApp.layout = html.Div( children=[ html.H1( children='Dash App' ) ] )


@flaskServer.route( '/', methods=[ 'GET' ] )
def hello_world():
    return 'Hello World!'


@flaskServer.route( '/customerupdate', methods=[ 'GET', 'POST' ] )
def customerupdate():
    posted_file = str( request.files[ 'document' ].read(), 'utf-8' )
    posted_data = json.load( request.files[ 'datas' ] )
    print( posted_file )
    print( posted_data )
    return '{}\n{}\n'.format( posted_file, posted_data )


def run():
    flaskServer.run( host='0.0.0.0', port=random.randint( 2000, 9000 ) )


def keep_alive():
    '''
    Creates and starts new thread that runs the function run.
    '''
    t = Thread( target=run )
    t.start()
