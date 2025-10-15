import streamlit as st
import pandas as pd
import asyncio
import json
from typing import List, Optional
import requests
import httpx
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

try:
    from st_aggrid import AgGrid, GridOptionsBuilder
    from st_aggrid.shared import GridUpdateMode
    AGGrid_AVAILABLE = True
except ImportError:
    AGGrid_AVAILABLE = False
    st.warning("streamlit_aggrid not available. Using basic table display.")

# Import our existing modules
from models import FetchRequest, NLQuery
from apollo import fetch_contacts
from apollo_organizations import search_organizations, get_organization_top_people
from hunter import verify_contacts_async
from hubspot import push_contacts_async, push_companies_async, push_people_to_companies_async
from utils import extract_contact_info

# Page configuration
st.set_page_config(
    page_title="Lead Researcher Pro",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .contact-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e1e5e9;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 0.375rem;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 0.375rem;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'contacts_data' not in st.session_state:
        st.session_state.contacts_data = []
    if 'search_history' not in st.session_state:
        st.session_state.search_history = []
    if 'api_keys' not in st.session_state:
        st.session_state.api_keys = {
            'apollo': '',
            'hunter': '',
            'hubspot': ''
        }
    if 'search_submitted' not in st.session_state:
        st.session_state.search_submitted = False

def save_api_keys():
    """Save API keys to session state"""
    st.session_state.api_keys = {
        'apollo': st.session_state.get('apollo_key', ''),
        'hunter': st.session_state.get('hunter_key', ''),
        'hubspot': st.session_state.get('hubspot_key', '')
    }

def load_api_keys():
    """Load API keys from session state"""
    return st.session_state.api_keys

def create_contact_dataframe(contacts: List[dict]) -> pd.DataFrame:
    """Convert contacts list to pandas DataFrame"""
    if not contacts:
        return pd.DataFrame()
    
    df = pd.DataFrame(contacts)
    # Select and rename columns for display
    display_columns = {
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'email': 'Email',
        'title': 'Title',
        'organization': 'Organization',
        'phone': 'Phone',
        'email_status': 'Email Status',
        'hunter_result': 'Verification Result',
        'hunter_score': 'Verification Score'
    }
    
    available_columns = {k: v for k, v in display_columns.items() if k in df.columns}
    df_display = df[list(available_columns.keys())].copy()
    df_display = df_display.rename(columns=available_columns)
    
    return df_display

def display_contact_metrics(contacts: List[dict]):
    """Display key metrics about the contacts"""
    if not contacts:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Contacts", len(contacts))
    
    with col2:
        verified = len([c for c in contacts if c.get('hunter_result') == 'deliverable'])
        st.metric("Verified Emails", verified)
    
    with col3:
        unique_orgs = len(set([c.get('organization', '') for c in contacts if c.get('organization')]))
        st.metric("Unique Organizations", unique_orgs)
    
    with col4:
        avg_score = sum([c.get('hunter_score', 0) for c in contacts if c.get('hunter_score')]) / len(contacts) if contacts else 0
        st.metric("Avg Verification Score", f"{avg_score:.1f}")

def display_contact_visualizations(contacts: List[dict]):
    """Display visualizations for the contacts data"""
    if not contacts:
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Email verification status pie chart
        verification_status = {}
        for contact in contacts:
            status = contact.get('hunter_result', 'Unknown')
            verification_status[status] = verification_status.get(status, 0) + 1
        
        if verification_status:
            fig = px.pie(
                values=list(verification_status.values()),
                names=list(verification_status.keys()),
                title="Email Verification Status"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top organizations bar chart
        org_counts = {}
        for contact in contacts:
            org = contact.get('organization', 'Unknown')
            if org and org != 'Unknown':
                org_counts[org] = org_counts.get(org, 0) + 1
        
        if org_counts:
            # Get top 10 organizations
            top_orgs = dict(sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:10])
            fig = px.bar(
                x=list(top_orgs.values()),
                y=list(top_orgs.keys()),
                orientation='h',
                title="Top Organizations"
            )
            fig.update_layout(yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)

def main():
    initialize_session_state()
    
    # Main content starts here
    
    # Sidebar for navigation and API keys
    with st.sidebar:
        # Header with logo
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h2 style="color: #1f77b4; margin: 0;">🔍 Lead Researcher Pro</h2>
            <p style="color: #666; margin: 0.5rem 0 0 0; font-size: 0.9rem;">Professional Lead Generation</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Navigation
        st.subheader("🧭 Search Methods")

        
        # Create navigation with icons and descriptions
        nav_options = {
            "🏢 Organization Search": "Search companies and get their key people",
            "🎯 Contact Search": "Advanced contact search with filters", 
            "🤖 AI Search": "Natural language contact queries",
            "📊 Results & Export": "View and export your data",
            "📈 Analytics": "Insights and visualizations"
        }
        
        selected_page = st.selectbox(
            "Choose your search method:",
            options=list(nav_options.keys()),
            format_func=lambda x: f"{x} - {nav_options[x]}"
        )
        
        st.markdown("---")
        
        # API Keys section
        st.subheader("🔑 API Configuration")
        
        with st.expander("🔧 API Keys", expanded=True):
            apollo_key = st.text_input(
                "Apollo.io API Key",
                value=st.session_state.get('apollo_key', ''),
                type="password",
                help="Your Apollo.io API key for lead data"
            )
            
            hunter_key = st.text_input(
                "Hunter.io API Key", 
                value=st.session_state.get('hunter_key', ''),
                type="password",
                help="Your Hunter.io API key for email verification"
            )
            
            hubspot_key = st.text_input(
                "HubSpot API Key",
                value=st.session_state.get('hubspot_key', ''),
                type="password", 
                help="Your HubSpot API key for CRM integration"
            )
            
            # Save API keys to session state
            st.session_state.apollo_key = apollo_key
            st.session_state.hunter_key = hunter_key
            st.session_state.hubspot_key = hubspot_key
            
            # API Status indicators
            st.markdown("**API Status:**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if apollo_key:
                    st.success("✅")
                else:
                    st.warning("⚠️")
            
            with col2:
                if hunter_key:
                    st.success("✅")
                else:
                    st.warning("⚠️")
            
            with col3:
                if hubspot_key:
                    st.success("✅")
                else:
                    st.warning("⚠️")
        
        st.markdown("---")
        
        # Quick stats
        if 'organizations_data' in st.session_state and st.session_state.organizations_data:
            st.subheader("📊 Session Stats")
            st.metric("Organizations Found", len(st.session_state.organizations_data))
            
            total_people = sum([len(st.session_state.get(f"people_{org['id']}", [])) 
                              for org in st.session_state.organizations_data 
                              if f"people_{org['id']}" in st.session_state])
            if total_people > 0:
                st.metric("People Discovered", total_people)
    
    # Main content area
    if selected_page == "🏢 Organization Search":
        organization_search_page()
    elif selected_page == "🎯 Contact Search":
        contact_search_page()
    elif selected_page == "🤖 AI Search":
        nl_search_page()
    elif selected_page == "📊 Results & Export":
        results_page()
    elif selected_page == "📈 Analytics":
        analytics_page()

def organization_search_page():
    """Organization search page"""
    st.header("🏢 Organization Search")
    
    st.info("🎉 Search for companies and discover their key decision makers. Perfect for B2B lead generation!")
    
    # Quick action buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🚀 Quick Start Guide"):
            st.markdown("""
            **Quick Start:**
            1. Enter organization keywords (e.g., "technology", "fintech")
            2. Select filters (industry, location, size)
            3. Click "Search Organizations"
            4. Get key people from each company
            5. Push to HubSpot for CRM integration
            """)
    
    with col2:
        if st.button("💡 Search Tips"):
            st.markdown("""
            **Best Practices:**
            - Start broad, then narrow down
            - Use industry keywords
            - Combine location + industry
            - Export data regularly
            """)
    
    with col3:
        if st.button("🔗 HubSpot Setup"):
            st.markdown("""
            **HubSpot Integration:**
            1. Create HubSpot Private App
            2. Enable CRM permissions
            3. Copy API key to sidebar
            4. Start pushing data!
            """)
    
    with st.form("organization_search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Search Parameters")
            
            org_keywords = st.text_input(
                "Organization Keywords",
                placeholder="e.g., technology, software, fintech",
                help="Keywords to search for in company profiles"
            )
            
            total_records = st.number_input(
                "Total Organizations",
                min_value=1,
                max_value=50,
                value=10,
                help="Number of organizations to retrieve"
            )
        
        with col2:
            st.subheader("Filters")
            
            # Organization industries
            industry_options = [
                "Technology", "Software", "SaaS", "Fintech", "Healthcare", "Biotech",
                "Education", "E-learning", "Finance", "Banking", "Insurance",
                "Real Estate", "Construction", "Manufacturing", "Retail", "E-commerce",
                "Media", "Entertainment", "Gaming", "Marketing", "Advertising",
                "Consulting", "Legal", "Government", "Non-profit", "Energy"
            ]
            
            selected_industries = st.multiselect(
                "Select Industries", 
                options=industry_options, 
                default=[],
                help="Select industries to filter organizations by"
            )
            
            # Organization locations
            location_options = [
                "San Francisco", "New York", "Los Angeles", "Chicago", "Boston", "Seattle",
                "Austin", "Denver", "Miami", "Atlanta", "Dallas", "Houston", "Phoenix",
                "Remote", "United States", "Canada", "United Kingdom", "Germany"
            ]
            
            selected_locations = st.multiselect(
                "Select Locations", 
                options=location_options, 
                default=[],
                help="Select geographic locations to filter by"
            )
            
            # Company sizes
            size_options = [
                "1-10", "11-50", "51-200", "201-500", "501-1000", 
                "1001-5000", "5001-10000", "10000+"
            ]
            
            selected_sizes = st.multiselect(
                "Select Company Sizes", 
                options=size_options, 
                default=[],
                help="Select company size ranges to filter by"
            )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            search_submitted = st.form_submit_button(
                "🔍 Search Organizations",
                use_container_width=True,
                type="primary"
            )
    
    if search_submitted:
        if not st.session_state.get('apollo_key'):
            st.error("Please enter your Apollo API key in the sidebar.")
            return
        
        if not org_keywords and not selected_industries and not selected_locations:
            st.error("Please enter at least one search criteria.")
            return
        
        with st.spinner("Searching for organizations..."):
            try:
                organizations = search_organizations(
                    api_key=st.session_state.apollo_key,
                    keywords=[org_keywords] if org_keywords else None,
                    locations=selected_locations if selected_locations else None,
                    industries=selected_industries if selected_industries else None,
                    company_sizes=selected_sizes if selected_sizes else None,
                    limit=total_records
                )
                
                st.session_state.organizations_data = organizations
                st.success(f"Found {len(organizations)} organizations!")
                
            except Exception as e:
                st.error(f"Error searching for organizations: {str(e)}")
    
    # Display organizations
    if 'organizations_data' in st.session_state and st.session_state.organizations_data:
        organizations = st.session_state.organizations_data
        
        st.markdown("---")
        
        # HubSpot integration buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🏢 Push All Organizations to HubSpot", disabled=not st.session_state.get('hubspot_key')):
                with st.spinner("Pushing organizations to HubSpot..."):
                    try:
                        hubspot_results = asyncio.run(push_companies_async(organizations, st.session_state.hubspot_key))
                        successful = len([r for r in hubspot_results if 'error' not in r])
                        st.success(f"✅ Pushed {successful} organizations to HubSpot!")
                        
                        # Store company IDs for future use
                        st.session_state.hubspot_company_ids = []
                        for result in hubspot_results:
                            if 'error' not in result and result.get('id'):
                                st.session_state.hubspot_company_ids.append(result['id'])
                                
                    except Exception as e:
                        st.error(f"❌ Error pushing to HubSpot: {str(e)}")
        
        with col2:
            if st.button("📊 Export Organizations as CSV"):
                if organizations:
                    df = pd.DataFrame(organizations)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"organizations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
        
        with col3:
            if st.button("🔄 Refresh Data"):
                st.rerun()
        
        st.markdown("---")
        st.subheader("📊 Found Organizations")
        
        # Display organizations in a nice format
        for i, org in enumerate(organizations):
            with st.expander(f"🏢 {org.get('name', 'Unknown Company')}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Industry:** {org.get('industry', 'N/A')}")
                    st.write(f"**Size:** {org.get('estimated_num_employees', 'N/A')} employees")
                    st.write(f"**Location:** {org.get('city', 'N/A')}, {org.get('state', 'N/A')}")
                
                with col2:
                    if org.get('website_url'):
                        st.write(f"**Website:** [{org['website_url']}]({org['website_url']})")
                    if org.get('linkedin_url'):
                        st.write(f"**LinkedIn:** [{org['linkedin_url']}]({org['linkedin_url']})")
                    if org.get('phone'):
                        st.write(f"**Phone:** {org['phone']}")
                
                # Buttons for getting people and HubSpot integration
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                with col_btn1:
                    if st.button(f"👥 Get Top People", key=f"people_{i}"):
                        with st.spinner("Getting top people..."):
                            try:
                                people = get_organization_top_people(
                                    api_key=st.session_state.apollo_key,
                                    organization_id=org['id']
                                )
                                
                                # Store people in session state for this organization
                                st.session_state[f"people_{org['id']}"] = people
                                
                                if people:
                                    st.success(f"Found {len(people)} top people!")
                                    
                                    # Display people
                                    for person in people:
                                        st.write(f"• **{person.get('first_name', '')} {person.get('last_name', '')}** - {person.get('title', 'N/A')}")
                                        if person.get('email'):
                                            st.write(f"  📧 {person['email']}")
                                        if person.get('linkedin_url'):
                                            st.write(f"  🔗 [LinkedIn]({person['linkedin_url']})")
                                else:
                                    st.info("No top people found for this organization.")
                                    
                            except Exception as e:
                                st.error(f"Error getting top people: {str(e)}")
                
                # Show people if already loaded
                if f"people_{org['id']}" in st.session_state:
                    people = st.session_state[f"people_{org['id']}"]
                    if people:
                        st.markdown("**👥 Top People:**")
                        for person in people:
                            st.write(f"• **{person.get('first_name', '')} {person.get('last_name', '')}** - {person.get('title', 'N/A')}")
                            if person.get('email'):
                                st.write(f"  📧 {person['email']}")
                            if person.get('linkedin_url'):
                                st.write(f"  🔗 [LinkedIn]({person['linkedin_url']})")
                        
                        # HubSpot integration for people
                        with col_btn2:
                            if st.button(f"📤 Push People to HubSpot", key=f"push_people_{i}", disabled=not st.session_state.get('hubspot_key')):
                                with st.spinner("Pushing people to HubSpot..."):
                                    try:
                                        # Find corresponding HubSpot company ID
                                        hubspot_company_id = None
                                        if 'hubspot_company_ids' in st.session_state and i < len(st.session_state.hubspot_company_ids):
                                            hubspot_company_id = st.session_state.hubspot_company_ids[i]
                                        
                                        if hubspot_company_id:
                                            results = asyncio.run(push_people_to_companies_async(people, hubspot_company_id, st.session_state.hubspot_key))
                                            successful = len([r for r in results if 'error' not in r])
                                            st.success(f"✅ Pushed {successful} people to HubSpot and linked to company!")
                                        else:
                                            # Push people without company association
                                            results = asyncio.run(push_contacts_async(people, st.session_state.hubspot_key))
                                            successful = len([r for r in results if 'error' not in r])
                                            st.success(f"✅ Pushed {successful} people to HubSpot!")
                                            
                                    except Exception as e:
                                        st.error(f"❌ Error pushing people to HubSpot: {str(e)}")
                        
                        with col_btn3:
                            if st.button(f"📊 Export People", key=f"export_people_{i}"):
                                df = pd.DataFrame(people)
                                csv = df.to_csv(index=False)
                                st.download_button(
                                    label="Download People CSV",
                                    data=csv,
                                    file_name=f"{org.get('name', 'company')}_people_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                    mime="text/csv"
                                )

def contact_search_page():
    """Contact search page with form inputs"""
    st.header("🎯 Advanced Contact Search")
    
    # Search tips
    with st.expander("💡 Search Tips for Better Results"):
        st.markdown("""
        **For best results:**
        1. **Start simple**: Use only keywords first, then add filters
        2. **Fewer filters**: Don't use more than 2-3 filters at once
        3. **Broader terms**: "engineer" instead of "senior software engineer"
        4. **Popular locations**: "New York", "San Francisco", "Remote"
        5. **Common titles**: "Manager", "Director", "CEO"
        
        **Example searches:**
        - Keywords: "engineer" (no filters)
        - Keywords: "manager" (no filters)
        - Keywords: "CEO" (no filters)
        - Keywords: "founder" (no filters)
        
        **If still no results:**
        - Try without any filters first
        - Use very broad keywords
        - Check if your Apollo plan has data access
        """)
    
    with st.form("contact_search_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Search Parameters")
            
            q_keywords = st.text_input(
                "Keywords",
                placeholder="e.g., software engineer, marketing manager",
                help="Keywords to search for in contact profiles"
            )
            
            total_records = st.number_input(
                "Total Records",
                min_value=1,
                max_value=1000,
                value=1,
                help="Number of contacts to retrieve"
            )
            
            per_page = st.number_input(
                "Records Per Page",
                min_value=1,
                max_value=25,
                value=1,
                help="Records per API request"
            )
            
            start_page = st.number_input(
                "Start Page",
                min_value=1,
                value=1,
                help="Page number to start from"
            )
        
        with col2:
            st.subheader("Filters")

            # Person titles (multi-select)
            job_titles = [
                "CEO", "CTO", "CFO", "COO", "President", "Vice President",
                "Manager", "Project Manager", "Director", "Senior Director",
                "Software Engineer", "Senior Software Engineer", "Lead Engineer",
                "Product Manager", "Marketing Manager", "Sales Manager",
                "Account Manager", "Business Development", "Operations Manager",
                "HR Manager", "Finance Manager", "General Manager",
                "Founder", "Co-Founder", "Owner", "Partner", "Consultant",
                "Analyst", "Specialist", "Coordinator", "Supervisor",
                "Administrative Assistant", "Executive Assistant"
            ]
            
            selected_titles = st.multiselect(
                "Select Job Titles", 
                options=job_titles, 
                default=[],
                help="Select job titles to filter contacts by"
            )
            person_titles = selected_titles if selected_titles else None
            
            # Organization keywords (multi-select)
            industry_keywords = [
                "Technology", "Software", "SaaS", "Fintech", "Healthcare", "Biotech",
                "Education", "E-learning", "Finance", "Banking", "Insurance",
                "Real Estate", "Construction", "Manufacturing", "Retail", "E-commerce",
                "Media", "Entertainment", "Gaming", "Marketing", "Advertising",
                "Consulting", "Legal", "Government", "Non-profit", "Energy",
                "Transportation", "Automotive", "Aerospace", "Telecommunications",
                "Food & Beverage", "Fashion", "Beauty", "Travel", "Hospitality"
            ]
            
            selected_industries = st.multiselect(
                "Select Industries", 
                options=industry_keywords, 
                default=[],
                help="Select industries to filter organizations by"
            )
            org_keywords = selected_industries if selected_industries else None
            
            # Organization locations (multi-select)
            common_locations = [
                "San Francisco", "New York", "Los Angeles", "Chicago", "Boston", "Seattle",
                "Austin", "Denver", "Miami", "Atlanta", "Dallas", "Houston", "Phoenix",
                "Philadelphia", "San Diego", "Portland", "Nashville", "Las Vegas",
                "Remote", "United States", "Canada", "United Kingdom", "Germany",
                "France", "Netherlands", "Australia", "Singapore", "India", "Brazil"
            ]
            
            selected_locations = st.multiselect(
                "Select Locations", 
                options=common_locations, 
                default=[],
                help="Select geographic locations to filter by"
            )
            org_locations = selected_locations if selected_locations else None
            
            # Employee ranges (multi-select)
            company_sizes = [
                "1-10", "11-50", "51-200", "201-500", "501-1000", 
                "1001-5000", "5001-10000", "10000+"
            ]
            
            selected_sizes = st.multiselect(
                "Select Company Sizes", 
                options=company_sizes, 
                default=[],
                help="Select company size ranges to filter by"
            )
            employee_ranges = selected_sizes if selected_sizes else None
        
        st.markdown("---")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            search_submitted = st.form_submit_button(
                "🔍 Search Contacts",
                use_container_width=True,
                type="primary"
            )
        
        # Clear previous search results when form is submitted
        if search_submitted:
            st.session_state.search_submitted = True
            st.session_state.contacts_data = []  # Clear previous results
    
    # Only process search if form was actually submitted (not on page reload)
    if search_submitted and st.session_state.search_submitted:
        if not st.session_state.get('apollo_key'):
            st.error("Please enter your Apollo API key in the sidebar.")
            st.session_state.search_submitted = False  # Reset flag
            return
        
        if not q_keywords:
            st.error("Please enter search keywords.")
            st.session_state.search_submitted = False  # Reset flag
            return
        
        # Show search tips for better results
        if len(selected_titles) > 3 or len(selected_industries) > 3 or len(selected_locations) > 3:
            st.warning("⚠️ Too many filters selected. Try reducing filters for better results.")
        
        if total_records > 50:
            st.info("💡 For better results, try searching with fewer records first (1-10), then increase if needed.")
        
        # Create search request
        search_request = FetchRequest(
            api_key=st.session_state.apollo_key,
            total_records=total_records,
            per_page=per_page,
            start_page=start_page,
            q_keywords=q_keywords,
            person_titles=person_titles,
            organization_keywords=org_keywords,
            organization_locations=org_locations,
            organization_num_employees_ranges=employee_ranges
        )
        
        with st.spinner("Searching for contacts..."):
            try:
                contacts = fetch_contacts(search_request)
                st.session_state.contacts_data = contacts
                
                # Add to search history
                search_entry = {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'query': q_keywords,
                    'results_count': len(contacts),
                    'filters': {
                        'person_titles': person_titles,
                        'org_keywords': org_keywords,
                        'org_locations': org_locations,
                        'employee_ranges': employee_ranges
                    }
                }
                st.session_state.search_history.insert(0, search_entry)
                
                st.success(f"Found {len(contacts)} contacts!")
                
            except Exception as e:
                st.error(f"Error searching for contacts: {str(e)}")
            finally:
                # Reset search flag after processing
                st.session_state.search_submitted = False

def nl_search_page():
    """Natural language search page"""
    st.header("🤖 Natural Language Search")
    st.markdown("Ask for contacts in natural language and let AI parse your request.")
    
    with st.form("nl_search_form"):
        nl_query = st.text_area(
            "Natural Language Query",
            placeholder="e.g., Find 20 software engineers at tech startups in San Francisco with 10-50 employees",
            height=100,
            help="Describe what kind of contacts you're looking for in natural language"
        )
        
        nl_total_records = st.number_input(
            "Number of Contacts",
            min_value=1,
            max_value=100,
            value=10
        )
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            nl_submitted = st.form_submit_button(
                "🤖 Parse & Search",
                use_container_width=True,
                type="primary"
            )
    
    if nl_submitted:
        if not st.session_state.get('apollo_key'):
            st.error("Please enter your Apollo API key in the sidebar.")
            return
        
        if not nl_query:
            st.error("Please enter a natural language query.")
            return
        
        st.warning("⚠️ Natural language parsing is not yet implemented. Please use the Contact Search page for now.")
        # TODO: Implement ai_parse_query_to_payload function

def results_page():
    """Results display and export page"""
    st.header("📊 Search Results")
    
    contacts = st.session_state.contacts_data
    
    if not contacts:
        st.info("No contacts found. Please perform a search first.")
        return
    
    # Display metrics
    display_contact_metrics(contacts)
    st.markdown("---")
    
    # Options for verification and HubSpot integration
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("✅ Verify Emails", disabled=not st.session_state.get('hunter_key')):
            with st.spinner("Verifying emails..."):
                try:
                    verified_contacts = asyncio.run(verify_contacts_async(contacts, st.session_state.hunter_key))
                    st.session_state.contacts_data = verified_contacts
                    st.success("Email verification completed!")
                except Exception as e:
                    st.error(f"Error verifying emails: {str(e)}")
    
    with col2:
        if st.button("📤 Push to HubSpot", disabled=not st.session_state.get('hubspot_key')):
            with st.spinner("Pushing to HubSpot..."):
                try:
                    hubspot_results = asyncio.run(push_contacts_async(contacts, st.session_state.hubspot_key))
                    st.success(f"Pushed {len(hubspot_results)} contacts to HubSpot!")
                except Exception as e:
                    st.error(f"Error pushing to HubSpot: {str(e)}")
    
    with col3:
        if st.button("🔄 Refresh Data"):
            st.rerun()
    
    st.markdown("---")
    
    # Display contacts in an interactive table
    if contacts:
        df = create_contact_dataframe(contacts)
        
        if not df.empty:
            if AGGrid_AVAILABLE:
                # Configure AgGrid
                gb = GridOptionsBuilder.from_dataframe(df)
                gb.configure_pagination(paginationAutoPageSize=True)
                gb.configure_side_bar()
                gb.configure_selection('multiple', use_checkbox=True, groupSelectsChildren="Group checkbox select children")
                gb.configure_default_column(enablePivot=True, enableValue=True, enableRowGroup=True)
                gridOptions = gb.build()
                
                # Display the grid
                grid_response = AgGrid(
                    df,
                    gridOptions=gridOptions,
                    data_return_mode='AS_INPUT',
                    update_mode='MODEL_CHANGED',
                    fit_columns_on_grid_load=True,
                    theme='alpine',
                    enable_enterprise_modules=True,
                    height=400
                )
            else:
                # Use basic Streamlit dataframe display
                st.subheader("📋 Contacts Data")
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=400
                )
            
            # Export functionality
            st.markdown("### 📥 Export Data")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("📊 Export as CSV"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
            
            with col2:
                if st.button("📋 Export as JSON"):
                    json_data = json.dumps(contacts, indent=2)
                    st.download_button(
                        label="Download JSON",
                        data=json_data,
                        file_name=f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
            
            with col3:
                if st.button("📧 Export Emails Only"):
                    emails = [contact.get('email', '') for contact in contacts if contact.get('email')]
                    email_text = '\n'.join(emails)
                    st.download_button(
                        label="Download Email List",
                        data=email_text,
                        file_name=f"emails_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                        mime="text/plain"
                    )

def analytics_page():
    """Analytics and insights page"""
    st.header("📈 Analytics & Insights")
    
    contacts = st.session_state.contacts_data
    
    if not contacts:
        st.info("No contacts found. Please perform a search first.")
        return
    
    # Display visualizations
    display_contact_visualizations(contacts)
    
    st.markdown("---")
    
    # Search history
    st.subheader("🔍 Search History")
    if st.session_state.search_history:
        history_df = pd.DataFrame(st.session_state.search_history)
        st.dataframe(history_df, use_container_width=True)
    else:
        st.info("No search history available.")

if __name__ == "__main__":
    main()
