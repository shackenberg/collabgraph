#! /usr/bin/env python
# -*- coding: utf-8 -*-

import re
import pygraphviz as pgv
from datetime import date

class Paper:
  def __init__(self):
    self.id = 0  
    self.authors=list()

  def addAuthor(self,author):
    self.authors.append(author)

  def getAuthorId(self,author):
    return self.authors.index(author)

  def updateAuthor(self,oldauthor,newauthor):
    self.authors.pop(self.authors.index(oldauthor))
    self.authors.append(newauthor)

  def getAuthors(self):
    return self.authors


class CGraph():
  def __init__(self):
    self.gr=pgv.AGraph()
    self.authors={}
    self.papers = list()
    self.paper_counter = 0
    self.connections={}
    self.filename = ""
    self.verbose = True
    self.web = False
    
  def run(self,filecontent, outputfilename = None):
    self.extractAuthors_fromBib(filecontent)  
    self.drawNodes()
    self.drawGraph(outputfilename)
    
  def run_with_mendeley_data(self, outputfilename = None):
    mendeley=self.auth_mendeley()
    self.extractAuthors_fromMendeley(mendeley)  
    self.drawNodes()
    self.drawGraph(outputfilename)
  
  def extractAuthors_fromBib(self,filecontent):
    # go through the lines to find the authors of 
    # each paper (/ entry in the bibtex file)
    for inputline in filecontent:
      line = inputline.lstrip()
      keyword = 'author ='
      pattern = re.compile('\s*(author)\s*(=)',re.IGNORECASE)
      line = re.sub(pattern,keyword, line)
      if line[:len(keyword)].lower() == keyword:        
        line = self.sanitizeLine(line)
        current_paper = Paper()
        self.paper_counter = self.paper_counter+1
        paper_authors = re.split(" and ",line[len(keyword):])
        for name in paper_authors:
            current_paper.id = self.paper_counter
            author = self.matchNames(name)
            if (self.validateAuthor(author) == 1):
                current_paper.addAuthor(author)
        self.papers.append(current_paper)
  
  def auth_mendeley(self):
    from mendeley_client import MendeleyClient
    mendeley = MendeleyClient(XXXXXXX, XXXXXXX) #get from dev.mendeley.com
    try:
        mendeley.load_keys()
    except IOError:
        mendeley.get_required_keys()
        mendeley.save_keys()
    return mendeley
    
  def extractAuthors_fromMendeley(self,mendeley):
    if self.verbose: print 'getting data from Mendeley, please wait'
    num_documents = mendeley.library()[u'total_results']
    documents = mendeley.library(items=num_documents)
    profilename = mendeley.profile_info('me')[u'main'][u'name']
    self.filename = profilename + '\'s library @ mendeley'
    paper_ids= documents[u'document_ids']
    for paper_id in paper_ids:
        paper_details = mendeley.document_details(paper_id)
        paper_authors = paper_details["authors"]
        self.paper_counter = self.paper_counter+1
        current_paper = Paper()
        for name in paper_authors:
            current_paper.id = self.paper_counter
            author = name['surname'] + ', ' + name['forename']
            author = self.matchNames(author)
            if (self.validateAuthor(author) == 1):
                current_paper.addAuthor(author)
        self.papers.append(current_paper) 

  def findnextAuthor(self,line,start,end,pivot):
      # finds the next author in the given text line
      pivot = line.lower().find(' and ',pivot+1,end)
      if pivot == -1:
        pivot = end
      author = line[start+1:pivot].lstrip().rstrip('"')
      start = pivot + 4
      return author, pivot, start
  
    
  def matchNames(self,author):
    # checks if the author is already known with an more complete name
    # i.e. substitues B. Gates with Bill Gates
    if author.find(',') == -1:
      for i in  range(len(author[author.find(' ')+1:]),-2,-1):
        temp_name = author[0:len(author)-author.find(' ')-i] + ' ' +author[author.find(' '):].lstrip()
        for paper in self.papers:
          if temp_name in paper.authors:
            paper.updateAuthor(temp_name,author)
      return author
    else:
      for i in range(len(author[author.find(',')+0:]),2,-1):
        temp_name=author[:author.find(',')+i]
        for paper in self.papers:
          if temp_name in paper.authors:
            paper.updateAuthor(temp_name,author)
    return author


  def sanitizeLine(self,line):
    line = ' '.join(line.split()) # remove tabs and double spaces see [1]
    try:
      line = line.decode('utf-8')
    except:
      line = line.decode('cp1252')    
    if line[-1] == ',':
      line = line[:-1]
    if re.match(re.compile('(author =)\s*(\").*(\")'),line) != None:
      line = re.sub('(author =)\s*(\")','author =',line)
    line = re.sub('[{}]','',line)
    line = re.sub('\~',u' ',line)
    line = re.sub('\"a',u'ä',line)
    line = re.sub('\"A',u'Ä',line)
    line = re.sub('\"o',u'ö',line)
    line = re.sub('\"O',u'Ö',line)
    line = re.sub('\"u',u'ü',line)
    line = re.sub('\"U',u'Ü',line)
    line = re.sub('\"s',u'ß',line)
    line = re.sub('\\ss',u'ß',line)
    line = re.sub('"','',line)
    # necessary to remove spaces at the end of the string (don't ask)
    line = ' '.join(line.split()) # remove tabs and double spaces see [1]
    return line

  
  def validateAuthor(self,author):  
    # very rudementary function to get rid not usefull author names
    if author == '':
      return 0
    if author.lower() == "others":
      return 0
    if author.lower() == "et al":
      return 0
    return 1


  def drawNodes(self):
    for paper in self.papers:
      if len(paper.authors) == 1:
        self.gr.add_node(paper.authors[0])
      for n in range(len(paper.authors)-1):
        for m in range(n+1,len(paper.authors)):
          authorA = paper.authors[n]
          authorB = paper.authors[m]
          author_pair = ''.join(sorted((paper.authors[n],paper.authors[m])))
          # checks if no connection already exists
          # if connection exists connection is deleted and redrawn with 
          # thicker line
          if self.connections.has_key(author_pair) == 0:
            self.connections[author_pair] = 1
            self.gr.add_edge((authorA,authorB))
          else:
            self.connections[author_pair] =  self.connections[author_pair] + 1
            self.gr.delete_edge(authorA,authorB)            
            self.gr.add_edge((authorA,authorB),penwidth=str(self.connections[author_pair]))

  def drawGraph(self, outputfilename = None):
    if outputfilename is None:
        outputfilename = self.filename
    self.gr.node_attr['fontname']='Helvetica'
    label = 'Co-authorship graph for ' + self.filename + ' by Collabgraph - ' + str(date.today())
    self.gr.graph_attr['label']= label
    self.gr.graph_attr['fontname']='Helvetica'
    self.gr.graph_attr['overlap']='Prism'
    self.gr.layout(prog='neato')
    self.image_filename = outputfilename + ".svg"
    self.gr.draw(self.image_filename)

    # uncomment to write dot files
    self.gr.write(outputfilename+'.dot')
    if self.verbose: print "output: ", self.image_filename
  

if __name__ == "__main__":
  import sys
  try:
    argument = sys.argv[1]
  except:
    print 'please give file name or enter -m for Mendeley'
    sys.exit()

  ## use mendeley
  if argument == '-m':
    graph = CGraph()
    graph.filename = 'mendeley'
    graph.run_with_mendeley_data()
  else:
  
  ## use bibtex file
    filename = argument
    print 'opening file ', filename 
    with open(filename,'r') as filedata:
      graph = CGraph()
      graph.filename = filename
      filedata = open(filename)
      graph.run(filedata)
    filedata.closed

#[1]  http://stackoverflow.com/questions/4241757/python-django-how-to-remove-extra-white-spaces-tabs-from-a-string
