#!/usr/bin/env python3
import click
import os
import json
import time
from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader, Template
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

class TemplateCompiler:
    def __init__(self, templates_dir, output_dir,context={}):
        self.env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(['html', 'xml'])
        )
        self.output_dir = output_dir
        self.context = context

    def get_html(self, file):
        template = self.env.get_template(file)
        return template.render(**self.context)

@click.group()
def cli():
    """
    Comando para utilizar el motor de Templates Jinja2 para escribir páginas web estáticas mas rápidamente.
    """
    pass

@cli.command()
def startproject():
    """
    Comando utilizado para crear un nuevo proyecto.
    """
    input_dir = click.prompt("Ingrese el directorio donde estarán los templates",default='./templates/')
    input_dir = os.path.abspath(input_dir)
    
    if not os.path.isdir( os.path.dirname(input_dir) ):
        click.echo("Directorio no valido")
        click.echo( input_dir )
        exit()

    output_dir = click.prompt("Ingrese el directorio donde se guardarán los archivos generados",default='./build/')
    output_dir = os.path.abspath(output_dir)
    if not os.path.isdir( os.path.dirname(output_dir) ):
        click.echo("Directorio no valido")
        exit()
    
    if input_dir == output_dir:
        click.echo("Los directorios no deben ser el mismo")
        exit() 
    
    if not os.path.isdir(input_dir):
        os.mkdir(input_dir)
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    templates = list(filter(lambda f: os.path.isfile(os.path.join(input_dir,f)), os.listdir(input_dir)))
    exclude_files = []
    if templates:
        click.echo(templates)
        input_file = click.prompt("Ingrese el nombre de un archivo que no se deseen compilar",default="")
        while input_file != '':
            if input_file in templates:
                exclude_files.append(input_file)
                templates.remove(input_file)
            click.echo(templates)
            input_file = click.prompt("Ingrese el nombre de un archivo que no se desee compilar",default="")
        
        click.confirm(f"Esta seguro que desea excluir los siguientes archivos? {exclude_files}",abort=True)

    # Se obtienen variables de contexto
    var_name = click.prompt("Ingrese el nombre de una variable de contexto que desee agregar",default="")
    

    settings = {
        'input_dir':input_dir,'output_dir':output_dir,'exclude':exclude_files
    }
    settings_filename = click.prompt("Ingrese el nombre del archivo donde se guardarán las configuraciones",default="settings.json")
    
    with open(settings_filename,'w') as settings_file:
        json.dump(settings,settings_file)

@cli.command()
@click.option('-v', '--verbose', is_flag=True)
@click.option('-f','--file',type=str, help="archivo a compilar si se desea compilar solo un archivo")
@click.option('-s','--settingsfile',default="settings.json", help="archivo de configuraciones del proyecto, por defecto el comando busca el archivo settings.json")
def compile(verbose, file,settingsfile):
    """
    Comando utilizado para compilar un template o todos los templates.
    """
    with open(settingsfile) as settings_file:
        # Se obtienen las configuraciones del proyecto
        settings = json.load(settings_file)

    compiler = TemplateCompiler(settings['input_dir'],settings['output_dir'])
    if file:
        # Si se especifico solo un archivo 
        output_dir = os.path.join(compiler.output_dir,file)
        with open(output_dir,'w') as output_file:
            output_file.write(compiler.get_html(file))
            if verbose: click.echo(f"{output_dir} generado")
    else:
        # Se compilan todos los archivos que no estan excluidos
        templates = [f for f in os.listdir(settings['input_dir']) if os.path.isfile(os.path.join(settings['input_dir'],f)) and f not in settings['exclude'] ]
        
        for t in templates:
            output_dir = os.path.join(compiler.output_dir,t)
            
            with open(output_dir,'w') as output_file:
                output_file.write(compiler.get_html(t))
                if verbose: click.echo(f"{output_dir} generado")
    
    if verbose: click.echo("Compilación terminada")
    

@cli.command()
@click.option('-v', '--verbose', is_flag=True)
@click.option('-s','--settingsfile',default="settings.json", help="archivo de configuraciones del proyecto, por defecto el comando busca el archivo settings.json")
def runserver(verbose, settingsfile):
    """
    Comando utilizado para ejecutar de manera continua un servidor que irá compilando los templates
    a medida que estos se modifican.
    """
    with open(settingsfile) as settings_file:
        # Se obtienen las configuraciones del proyecto
        settings = json.load(settings_file)
    
    if verbose: click.echo("Iniciando Servidor...")
    compiler = TemplateCompiler(settings['input_dir'],settings['output_dir'])
    patterns = "*"
    ignore_patterns = ""
    ignore_directories = True
    case_sensitive = True
    my_event_handler = PatternMatchingEventHandler(patterns, ignore_patterns, ignore_directories, case_sensitive)
    
    def on_modified(event):
        """Funcion encargada de manejar un archivo cuando es modificado"""
        filename = os.path.basename(event.src_path)
        
        if filename not in settings['exclude']:
            output_dir = os.path.join(compiler.output_dir,filename)
            
            with open(output_dir,'w') as output_file:
                output_file.write(compiler.get_html(filename))
                if verbose: click.echo(f"{output_dir} generado")
        
        
    my_event_handler.on_modified = on_modified
    path = settings['input_dir']
    go_recursively = False
    my_observer = Observer()
    my_observer.schedule(my_event_handler, path, recursive=go_recursively)
    my_observer.start()

    click.echo("Presione Ctrl + C para finalizar...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if verbose: click.echo("Finalizando servidor")
        my_observer.stop()
        my_observer.join()
    
    