# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
# Name:         documentation/make.py
# Purpose:      music21 documentation script, v. 2.0
#
# Authors:      Josiah Wolf Oberholtzer
#               Christopher Ariza
#               Michael Scott Cuthbert
#
# Copyright:    Copyright © 2013-17 Michael Scott Cuthbert and the music21 Project
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------

import os
import shutil
import textwrap
import webbrowser

from music21 import common
from music21 import exceptions21

from . import writers

class DocBuilderException(exceptions21.Music21Exception):
    pass

class DocBuilder:
    def __init__(self, command='html'):
        self.useMultiprocessing = True
        self.cpus_to_use = common.cpus()
        if self.cpus_to_use == 1:
            self.useMultiprocessing = False
        self.useMultiprocessing = False  # too unstable still
        self.documentationDirectoryPath = None
        self.autogenDirectoryPath = None
        self.buildDirectoryPath = None
        self.doctreesDirectoryPath = None
        self.sourcesDirectoryPath = None
        self.buildDirectories = {}
        self.command = command
        self.getPaths()


    def run(self):
        if self.command == 'clean':
            self.runClean()
        elif self.command == 'help':
            self.print_usage()
        else:
            self.runBuild()
            self.postBuild()

    def runClean(self):
        print('CLEANING AUTOGENERATED DOCUMENTATION')
        shutil.rmtree(self.autogenDirectoryPath)
        os.mkdir(self.autogenDirectoryPath)
        print('CLEANING BUILT DOCUMENTATION')
        shutil.rmtree(self.buildDirectoryPath)
        os.mkdir(self.buildDirectoryPath)

    def runBuild(self, runSphinx=True):
        if self.command not in self.buildDirectories:
            self.print_usage()
            raise DocBuilderException(
                f'I do not understand the command {self.command}. exiting')

        if not os.path.exists(self.autogenDirectoryPath):
            os.mkdir(self.autogenDirectoryPath)
        if not os.path.exists(self.buildDirectoryPath):
            os.mkdir(self.buildDirectoryPath)
        if not os.path.exists(self.buildDirectories[self.command]):
            os.mkdir(self.buildDirectories[self.command])
        if not os.path.exists(self.doctreesDirectoryPath):
            os.mkdir(self.doctreesDirectoryPath)

        print('WRITING DOCUMENTATION FILES')
        writers.StaticFileCopier().run()
        try:
            writers.IPythonNotebookReSTWriter().run()
        except OSError:
            raise ImportError('IPythonNotebookReSTWriter crashed; most likely cause: '
                              + 'no pandoc installed: https://github.com/jgm/pandoc/releases')

        writers.ModuleReferenceReSTWriter().run()
        writers.CorpusReferenceReSTWriter().run()

        if runSphinx:
            self.runSphinx()

    def runSphinx(self):
        try:
            import sphinx
        except ImportError:
            message = 'Sphinx is required to build documentation; '
            message += 'download from http://sphinx-doc.org'
            raise ImportError(message)

        target = self.command
        if target == 'latexpdf':
            target = 'latex'
        # other options are in source/conf.py,

        # sphinx changed their main processing in v. 1.7; see
        # https://github.com/sphinx-doc/sphinx/pull/3668
        sphinx_version = tuple(sphinx.__version__.split('.'))
        sphinx_new = False
        if tuple(int(x) for x in sphinx_version[0:2]) < (1, 7):
            sphinxOptions = ['sphinx']
        else:
            sphinxOptions = []
            sphinx_new = True

        sphinxOptions.extend(('-b', target))
        sphinxOptions.extend(('-c', self.sourcesDirectoryPath))
        sphinxOptions.extend(('-d', self.doctreesDirectoryPath))
        if self.useMultiprocessing:
            sphinxOptions.extend(('-j', str(self.cpus_to_use)))
        sphinxOptions.append(self.autogenDirectoryPath)
        sphinxOptions.append(self.buildDirectories[target])
        # sphinx.main() returns 0 on success, 1 on failure.
        # If the docs fail to build, we should not try to open a web browser.
        returnCode = 0

        if sphinx_new:
            # noinspection PyPackageRequirements
            import sphinx.cmd.build  # pylint: disable=import-error
            sphinx_main_command = sphinx.cmd.build.main
        else:
            sphinx_main_command = sphinx.main

        try:  # pylint: disable=assignment-from-no-return
            returnCode = sphinx_main_command(sphinxOptions)
        except SystemExit:
            returnCode = 0

        if returnCode == 1:
            raise DocBuilderException(
                'Build failed (or nothing to build), no web browser being launched.'
            )



    def getPaths(self):
        documentationDirectoryPath = os.path.join(common.getRootFilePath(), 'documentation')
        self.documentationDirectoryPath = documentationDirectoryPath
        self.autogenDirectoryPath = os.path.join(documentationDirectoryPath, 'autogenerated')
        self.buildDirectoryPath = os.path.join(documentationDirectoryPath, 'build')
        self.doctreesDirectoryPath = os.path.join(self.buildDirectoryPath, 'doctrees')
        self.sourcesDirectoryPath = os.path.join(documentationDirectoryPath, 'source')
        self.buildDirectories = {
            'html': os.path.join(self.buildDirectoryPath, 'html'),
            'latex': os.path.join(self.buildDirectoryPath, 'latex'),
            # could reuse latex, but too much rewriting
            'latexpdf': os.path.join(self.buildDirectoryPath, 'latex'),
            'linkcheck': os.path.join(self.buildDirectoryPath, 'linkcheck'),
        }



    def print_usage(self):
        usage = textwrap.dedent('''
            m21 Documentation build script:

                documentation$ python ./make.py [COMMAND]

            Currently supported command are:

                html:     build HTML documentation
                latex:    build LaTeX sources
                latexpdf: build PDF from LaTeX source
                linkcheck:check external links
                clean:    remove autogenerated files
                help:     print this message

            Note that the Braille unicode files tend to break latexpdf.
        ''')

        print(usage)

    def postBuild(self):
        if self.command == 'html':
            self.launchWeb()
        elif self.command == 'latexpdf':
            self.latexPdf()

    def launchWeb(self):
        launchPath = os.path.join(
            self.buildDirectories['html'],
            'index.html',
        )

        if launchPath.startswith('/'):
            launchPath = 'file://' + launchPath
        print('Attempting to launch web browser. If this hangs, hit Ctrl-C with no worries')
        webbrowser.open(launchPath)

    def latexPdf(self):
        with common.cd(self.buildDirectories['latex']):
            os.system('make all-pdf')
